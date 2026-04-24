"""Regression runner helpers for the evaluation harness.

Thin re-export of mock and report modules for backward compatibility.
"""

from __future__ import annotations

from tests.eval.regression_mock import _mock_run_pipeline
from tests.eval.regression_report import (
    _detect_regression,
    _load_baseline,
    _mean,
    generate_markdown_report,
)

__all__ = [
    "_detect_regression",
    "_load_baseline",
    "_mean",
    "_mock_run_pipeline",
    "generate_markdown_report",
]
