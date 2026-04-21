"""Tests for the evaluation harness modules.

Covers golden_set, scoring, and regression_runner with high coverage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.eval.golden_set import (
    GOLDEN_SET,
    EvalQuery,
    ExpectedVerdict,
    get_by_category,
    get_by_id,
)
from tests.eval.regression_runner import (
    _detect_regression,
    _load_baseline,
    _mean,
    _mock_run_pipeline,
    generate_markdown_report,
    main,
    run_eval,
)
from tests.eval.scoring import (
    EvalScores,
    compute_composite_score,
    score_adversary_catch_rate,
    score_citation_accuracy,
    score_claim_recall,
    score_independence,
    score_run,
)


class TestGoldenSet:
    def test_golden_set_has_20_queries(self) -> None:
        assert len(GOLDEN_SET) == 20

    def test_all_ids_are_unique(self) -> None:
        ids = [q.id for q in GOLDEN_SET]
        assert len(ids) == len(set(ids))

    def test_categories_distribution(self) -> None:
        counts: dict[str, int] = {}
        for q in GOLDEN_SET:
            counts[q.category] = counts.get(q.category, 0) + 1
        assert counts.get("factual", 0) == 4
        assert counts.get("subjective", 0) == 4
        assert counts.get("unanswerable", 0) == 4
        assert counts.get("sensitive", 0) == 4
        assert counts.get("ambiguous", 0) == 4

    def test_get_by_category_factual(self) -> None:
        factual = get_by_category("factual")
        assert len(factual) == 4
        assert all(q.category == "factual" for q in factual)

    def test_get_by_category_empty_for_unknown(self) -> None:
        assert get_by_category("nonexistent") == []  # type: ignore[arg-type]

    def test_get_by_id_found(self) -> None:
        q = get_by_id("FACT-001")
        assert q is not None
        assert q.text == "What is the capital of France?"

    def test_get_by_id_not_found(self) -> None:
        assert get_by_id("UNKNOWN") is None

    def test_eval_query_model(self) -> None:
        ev = ExpectedVerdict(
            claim_text="test", verdict="SUPPORTED", min_evidence_count=1
        )
        q = EvalQuery(
            id="TEST-001",
            text="Test query",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[ev],
            notes="note",
        )
        assert q.id == "TEST-001"
        assert q.category == "factual"
        assert len(q.expected_verdicts) == 1


class TestScoringClaimRecall:
    def test_perfect_recall(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="Paris is the capital of France.",
                    verdict="SUPPORTED",
                )
            ],
        )
        actual = ["Paris is the capital of France."]
        assert score_claim_recall(q, actual) == 1.0

    def test_partial_recall(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=2,
            expected_citation_count=2,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="Paris is the capital of France.",
                    verdict="SUPPORTED",
                ),
                ExpectedVerdict(
                    claim_text="Berlin is the capital of Germany.",
                    verdict="SUPPORTED",
                ),
            ],
        )
        actual = ["Paris is the capital of France."]
        assert score_claim_recall(q, actual) == 0.5

    def test_zero_expected_claims_with_none_actual(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="sensitive",
            expected_claim_count=0,
            expected_citation_count=0,
            expected_verdicts=[],
        )
        assert score_claim_recall(q, []) == 1.0

    def test_zero_expected_claims_with_some_actual(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="sensitive",
            expected_claim_count=0,
            expected_citation_count=0,
            expected_verdicts=[],
        )
        assert score_claim_recall(q, ["unexpected claim"]) == 0.0

    def test_fuzzy_match_threshold(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="The quick brown fox jumps over the lazy dog.",
                    verdict="SUPPORTED",
                )
            ],
        )
        actual = ["The quick brown fox jumps over the lazy dog."]
        assert score_claim_recall(q, actual, threshold=0.9) == 1.0

    def test_fuzzy_match_fails_below_threshold(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="Completely different sentence about nothing similar.",
                    verdict="SUPPORTED",
                )
            ],
        )
        actual = ["This is an unrelated claim."]
        assert score_claim_recall(q, actual) == 0.0


class TestScoringCitationAccuracy:
    def test_all_supporting(self) -> None:
        assert (
            score_citation_accuracy(
                ["c1"], ["a", "b"], supporting_citations=["a", "b"]
            )
            == 1.0
        )

    def test_half_supporting(self) -> None:
        assert (
            score_citation_accuracy(
                ["c1"], ["a", "b"], supporting_citations=["a"]
            )
            == 0.5
        )

    def test_no_citations(self) -> None:
        assert score_citation_accuracy(["c1"], []) == 0.0

    def test_no_citations_no_claims(self) -> None:
        assert score_citation_accuracy([], []) == 1.0

    def test_none_supporting_citations(self) -> None:
        assert score_citation_accuracy(["c1"], ["a", "b"]) == 1.0


class TestScoringIndependence:
    def test_all_unique(self) -> None:
        assert score_independence(["a", "b", "c"]) == 1.0

    def test_some_duplicates(self) -> None:
        assert score_independence(["a", "a", "b"]) == 2 / 3

    def test_empty(self) -> None:
        assert score_independence([]) == 0.0

    def test_with_syndication_clusters(self) -> None:
        publishers = ["a", "b", "c", "d"]
        clusters = [["a", "b"]]
        result = score_independence(publishers, clusters)
        assert result == 3 / 4

    def test_cluster_with_no_overlap(self) -> None:
        publishers = ["a", "b"]
        clusters = [["c", "d"]]
        assert score_independence(publishers, clusters) == 1.0


class TestScoringAdversaryCatchRate:
    def test_all_caught(self) -> None:
        assert score_adversary_catch_rate(["false"], ["false"]) == 1.0

    def test_half_caught(self) -> None:
        assert (
            score_adversary_catch_rate(["false1", "false2"], ["false1"]) == 0.5
        )

    def test_no_false_claims(self) -> None:
        assert score_adversary_catch_rate([], ["something"]) == 1.0

    def test_fuzzy_catch(self) -> None:
        false_claims = ["The moon is made of green cheese"]
        caught = ["moon made of green cheese"]
        assert score_adversary_catch_rate(false_claims, caught) == 1.0


class TestScoringCompositeScore:
    def test_default_weights(self) -> None:
        result = compute_composite_score(1.0, 1.0, 1.0, 1.0)
        assert result == 1.0

    def test_zero_weights(self) -> None:
        result = compute_composite_score(1.0, 1.0, 1.0, 1.0, weights={})
        assert result == 0.0

    def test_custom_weights(self) -> None:
        weights = {"claim_recall": 1.0}
        result = compute_composite_score(0.5, 0.0, 0.0, 0.0, weights=weights)
        assert result == 0.5

    def test_all_zero_scores(self) -> None:
        result = compute_composite_score(0.0, 0.0, 0.0, 0.0)
        assert result == 0.0


class TestScoreRun:
    def test_full_run(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="Paris is the capital of France.",
                    verdict="SUPPORTED",
                )
            ],
        )
        scores = score_run(
            query=q,
            actual_claims=["Paris is the capital of France."],
            actual_citations=["https://example.com"],
            publisher_ids=["pub1"],
            false_claims=[],
            caught_claims=[],
            supporting_citations=["https://example.com"],
        )
        assert isinstance(scores, EvalScores)
        assert scores.claim_recall == 1.0
        assert scores.citation_accuracy == 1.0
        assert scores.independence_score == 1.0
        assert scores.adversary_catch_rate == 1.0
        assert scores.composite_score == 1.0

    def test_eval_scores_to_dict(self) -> None:
        scores = EvalScores(
            claim_recall=0.5,
            citation_accuracy=0.6,
            independence_score=0.7,
            adversary_catch_rate=0.8,
            composite_score=0.9,
        )
        d = scores.to_dict()
        assert d["claim_recall"] == 0.5
        assert d["citation_accuracy"] == 0.6
        assert d["independence_score"] == 0.7
        assert d["adversary_catch_rate"] == 0.8
        assert d["composite_score"] == 0.9


class TestRegressionRunnerMockPipeline:
    def test_factual_mock(self) -> None:
        q = get_by_id("FACT-001")
        assert q is not None
        result = _mock_run_pipeline(q)
        assert len(result["actual_claims"]) == 1
        assert len(result["actual_citations"]) == 2
        assert len(result["publisher_ids"]) == 2

    def test_sensitive_mock(self) -> None:
        q = get_by_id("SENS-001")
        assert q is not None
        result = _mock_run_pipeline(q)
        assert result["actual_claims"] == []
        assert result["actual_citations"] == []

    def test_unanswerable_mock(self) -> None:
        q = get_by_id("UNAN-001")
        assert q is not None
        result = _mock_run_pipeline(q)
        assert result["actual_claims"] == []
        assert result["actual_citations"] == []


class TestRegressionRunnerHelpers:
    def test_mean(self) -> None:
        assert _mean([1.0, 2.0, 3.0]) == 2.0

    def test_mean_empty(self) -> None:
        assert _mean([]) == 0.0

    def test_load_baseline_flat(self, tmp_path: Path) -> None:
        path = tmp_path / "baseline.json"
        path.write_text(json.dumps({"claim_recall": 0.8}))
        result = _load_baseline(path)
        assert result["claim_recall"] == 0.8

    def test_load_baseline_with_aggregate(self, tmp_path: Path) -> None:
        path = tmp_path / "baseline.json"
        path.write_text(json.dumps({"aggregate": {"claim_recall": 0.8}}))
        result = _load_baseline(path)
        assert result["claim_recall"] == 0.8

    def test_detect_regression_no_regression(self) -> None:
        current = {"claim_recall": 0.8}
        baseline = {"claim_recall": 0.82}
        result = _detect_regression(current, baseline)
        assert result["regressed"] is False
        assert result["details"] == []

    def test_detect_regression_with_regression(self) -> None:
        current = {"claim_recall": 0.7}
        baseline = {"claim_recall": 0.82}
        result = _detect_regression(current, baseline)
        assert result["regressed"] is True
        assert len(result["details"]) == 1
        assert result["details"][0]["metric"] == "claim_recall"

    def test_detect_regression_multiple_metrics(self) -> None:
        current = {"a": 0.7, "b": 0.9}
        baseline = {"a": 0.82, "b": 0.95}
        result = _detect_regression(current, baseline)
        assert result["regressed"] is True
        assert len(result["details"]) == 1

    def test_detect_regression_ignores_missing_baseline_keys(self) -> None:
        current = {"a": 0.7, "b": 0.9}
        baseline = {"a": 0.82}
        result = _detect_regression(current, baseline)
        assert result["regressed"] is True
        assert len(result["details"]) == 1


class TestRegressionRunnerRunEval:
    def test_run_eval_without_baseline(self) -> None:
        result = run_eval()
        assert result["total_queries"] == 20
        assert "aggregate" in result
        assert "per_query" in result
        assert len(result["per_query"]) == 20
        assert result["baseline"] is None
        assert result["regression"] is None

    def test_run_eval_with_baseline(self, tmp_path: Path) -> None:
        baseline = {
            "aggregate": {
                "claim_recall": 1.0,
                "citation_accuracy": 1.0,
                "independence_score": 1.0,
                "adversary_catch_rate": 1.0,
                "composite_score": 1.0,
            }
        }
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(baseline))
        result = run_eval(baseline_path=baseline_path)
        assert result["baseline"] is not None
        assert result["regression"] is not None


class TestRegressionRunnerMarkdown:
    def test_generate_markdown_contains_header(self) -> None:
        result = run_eval()
        md = generate_markdown_report(result)
        assert "# Research Pipeline Evaluation Report" in md

    def test_generate_markdown_contains_aggregate(self) -> None:
        result = run_eval()
        md = generate_markdown_report(result)
        assert "## Aggregate Scores" in md
        assert "Claim Recall" in md

    def test_generate_markdown_contains_per_query(self) -> None:
        result = run_eval()
        md = generate_markdown_report(result)
        assert "## Per-Query Results" in md
        assert "FACT-001" in md

    def test_generate_markdown_with_regression(self, tmp_path: Path) -> None:
        baseline = {
            "aggregate": {
                "claim_recall": 1.0,
                "citation_accuracy": 1.0,
                "independence_score": 1.0,
                "adversary_catch_rate": 1.0,
                "composite_score": 1.0,
            }
        }
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(baseline))
        result = run_eval(baseline_path=baseline_path)
        md = generate_markdown_report(result)
        assert "## Baseline Comparison" in md
        assert "REGRESSION DETECTED" in md

    def test_generate_markdown_without_regression(
        self, tmp_path: Path
    ) -> None:
        result = run_eval()
        md = generate_markdown_report(result)
        if "## Baseline Comparison" in md:
            assert "No regression detected" in md


class TestRegressionRunnerCLI:
    def test_main_no_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main([])
        assert code == 0
        captured = capsys.readouterr()
        assert "Research Pipeline Evaluation Report" in captured.out

    def test_main_with_current_output(self, tmp_path: Path) -> None:
        current_path = tmp_path / "current.json"
        code = main(["--current", str(current_path)])
        assert code == 0
        assert current_path.exists()
        data = json.loads(current_path.read_text())
        assert data["total_queries"] == 20

    def test_main_with_regression(self, tmp_path: Path) -> None:
        baseline = {
            "aggregate": {
                "claim_recall": 1.0,
                "citation_accuracy": 1.0,
                "independence_score": 1.0,
                "adversary_catch_rate": 1.0,
                "composite_score": 1.0,
            }
        }
        baseline_path = tmp_path / "baseline.json"
        baseline_path.write_text(json.dumps(baseline))
        code = main(["--baseline", str(baseline_path)])
        assert code == 1

    def test_main_with_output_file(self, tmp_path: Path) -> None:
        output_path = tmp_path / "report.md"
        code = main(["--output", str(output_path)])
        assert code == 0
        assert output_path.exists()
        content = output_path.read_text()
        assert "# Research Pipeline Evaluation Report" in content

    def test_main_help(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
