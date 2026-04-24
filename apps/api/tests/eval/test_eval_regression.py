"""Tests for the regression runner in the evaluation harness."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.eval.golden_set import get_by_id
from tests.eval.regression_helpers import (
    _detect_regression,
    _load_baseline,
    _mean,
    _mock_run_pipeline,
    generate_markdown_report,
)
from tests.eval.regression_runner import main, run_eval

if TYPE_CHECKING:
    from pathlib import Path


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
