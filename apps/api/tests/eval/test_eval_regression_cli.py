"""CLI tests for the evaluation regression runner."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tests.eval.regression_runner import main

if TYPE_CHECKING:
    from pathlib import Path


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
