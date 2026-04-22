"""Additional scoring function tests for the evaluation harness."""

from __future__ import annotations

from tests.eval.golden_set import EvalQuery, ExpectedVerdict
from tests.eval.scoring import EvalScores, compute_composite_score, score_run
from tests.eval.scoring_metrics import score_adversary_catch_rate


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
