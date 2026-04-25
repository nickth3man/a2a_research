"""Regression runner CLI for the research pipeline evaluation harness."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tests.eval.golden_set import GOLDEN_SET
from tests.eval.regression_helpers import (
    _detect_regression,
    _load_baseline,
    _mean,
    _mock_run_pipeline,
    generate_markdown_report,
)
from tests.eval.scoring import score_run

__all__ = [
    "_detect_regression",
    "_load_baseline",
    "_mean",
    "_mock_run_pipeline",
    "generate_markdown_report",
    "main",
    "run_eval",
]


def run_eval(baseline_path: Path | None = None) -> dict[str, Any]:
    """Run the evaluation harness against the full golden set."""
    per_query: list[dict[str, Any]] = []
    claim_recall_scores: list[float] = []
    citation_accuracy_scores: list[float] = []
    independence_scores: list[float] = []
    adversary_scores: list[float] = []
    composite_scores: list[float] = []

    for query in GOLDEN_SET:
        result = _mock_run_pipeline(query)
        scores = score_run(
            query=query,
            actual_claims=result["actual_claims"],
            actual_citations=result["actual_citations"],
            publisher_ids=result["publisher_ids"],
            false_claims=result["false_claims"],
            caught_claims=result["caught_claims"],
            supporting_citations=result["supporting_citations"],
        )

        claim_recall_scores.append(scores.claim_recall)
        citation_accuracy_scores.append(scores.citation_accuracy)
        independence_scores.append(scores.independence_score)
        adversary_scores.append(scores.adversary_catch_rate)
        composite_scores.append(scores.composite_score)

        per_query.append(
            {
                "query_id": query.id,
                "query_text": query.text,
                "category": query.category,
                "scores": scores.to_dict(),
            }
        )

    aggregate = {
        "claim_recall": _mean(claim_recall_scores),
        "citation_accuracy": _mean(citation_accuracy_scores),
        "independence_score": _mean(independence_scores),
        "adversary_catch_rate": _mean(adversary_scores),
        "composite_score": _mean(composite_scores),
    }

    baseline: dict[str, float] | None = None
    regression: dict[str, Any] | None = None
    if baseline_path is not None and baseline_path.exists():
        baseline = _load_baseline(baseline_path)
        regression = _detect_regression(aggregate, baseline)

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "total_queries": len(GOLDEN_SET),
        "per_query": per_query,
        "aggregate": aggregate,
        "baseline": baseline,
        "regression": regression,
    }


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI parser."""
    parser = argparse.ArgumentParser(
        prog="regression_runner",
        description="Run the research pipeline eval harness and compare"
        " against a baseline.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Path to a JSON file containing baseline scores.",
    )
    parser.add_argument(
        "--current",
        type=Path,
        default=None,
        help="Path to write the current run JSON results.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write the markdown report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Returns:
        0 on success, 1 if a regression > 5% is detected.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    result = run_eval(baseline_path=args.baseline)

    if args.current:
        with open(args.current, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2)

    report = generate_markdown_report(result)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(report)
    else:
        print(report)

    regression = result.get("regression")
    if regression and regression["regressed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
