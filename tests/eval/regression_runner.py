"""Regression runner CLI for the research pipeline evaluation harness.

Loads the golden set, runs the pipeline (mock for now), computes scores,
compares current vs baseline, and generates a markdown report.

Usage::

    uv run python -m tests.eval.regression_runner --help
    uv run python -m tests.eval.regression_runner --output report.md
    uv run python -m tests.eval.regression_runner --baseline baseline.json --current current.json --output report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tests.eval.golden_set import GOLDEN_SET, EvalQuery
from tests.eval.scoring import score_run


def _mock_run_pipeline(query: EvalQuery) -> dict[str, Any]:
    """Mock pipeline runner that returns deterministic synthetic results.

    In production this would invoke ``a2a_research.workflow.coordinator.run_research``.
    The mock returns enough structure for the scoring functions to compute metrics.
    """
    category = query.category
    if category == "factual":
        actual_claims = [ev.claim_text for ev in query.expected_verdicts]
        actual_citations = [
            f"https://example.com/cite{i}"
            for i in range(query.expected_citation_count)
        ]
        publisher_ids = [
            f"publisher_{i % 3}" for i in range(len(actual_citations))
        ]
        false_claims: list[str] = []
        caught_claims: list[str] = []
    elif category == "subjective":
        actual_claims = [ev.claim_text for ev in query.expected_verdicts]
        actual_citations = [
            f"https://example.com/review{i}"
            for i in range(query.expected_citation_count)
        ]
        publisher_ids = [
            f"publisher_{i % 4}" for i in range(len(actual_citations))
        ]
        false_claims = []
        caught_claims = []
    elif category == "unanswerable":
        actual_claims = [ev.claim_text for ev in query.expected_verdicts]
        actual_citations = []
        publisher_ids = []
        false_claims = []
        caught_claims = []
    elif category == "sensitive":
        actual_claims = []
        actual_citations = []
        publisher_ids = []
        false_claims = []
        caught_claims = []
    elif category == "ambiguous":
        actual_claims = [ev.claim_text for ev in query.expected_verdicts]
        actual_citations = [
            f"https://example.com/sense{i}"
            for i in range(query.expected_citation_count)
        ]
        publisher_ids = [
            f"publisher_{i % 3}" for i in range(len(actual_citations))
        ]
        false_claims = []
        caught_claims = []
    else:
        actual_claims = []
        actual_citations = []
        publisher_ids = []
        false_claims = []
        caught_claims = []

    return {
        "actual_claims": actual_claims,
        "actual_citations": actual_citations,
        "publisher_ids": publisher_ids,
        "false_claims": false_claims,
        "caught_claims": caught_claims,
        "supporting_citations": actual_citations,
    }


def run_eval(baseline_path: Path | None = None) -> dict[str, Any]:
    """Run the evaluation harness against the full golden set.

    Args:
        baseline_path: Optional path to a JSON file containing baseline scores.

    Returns:
        A dictionary with per-query scores, aggregate scores, and baseline comparison.
    """
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


def _mean(values: list[float]) -> float:
    """Return the arithmetic mean of a list of floats."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _load_baseline(path: Path) -> dict[str, float]:
    """Load baseline scores from a JSON file."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if "aggregate" in data:
        return data["aggregate"]
    return data


def _detect_regression(
    current: dict[str, float], baseline: dict[str, float]
) -> dict[str, Any]:
    """Compare current scores against baseline and flag regressions > 5%.

    Returns a dictionary with regression details per metric and an overall
    ``regressed`` boolean.
    """
    THRESHOLD = 0.05
    details: list[dict[str, Any]] = []
    regressed = False

    for key in current:
        if key not in baseline:
            continue
        diff = baseline[key] - current[key]
        if diff > THRESHOLD:
            regressed = True
            details.append(
                {
                    "metric": key,
                    "baseline": baseline[key],
                    "current": current[key],
                    "diff": diff,
                    "threshold": THRESHOLD,
                }
            )

    return {"regressed": regressed, "details": details}


def generate_markdown_report(result: dict[str, Any]) -> str:
    """Generate a markdown report from evaluation results.

    Args:
        result: Output dictionary from :func:`run_eval`.

    Returns:
        A markdown-formatted string.
    """
    lines: list[str] = []
    lines.append("# Research Pipeline Evaluation Report")
    lines.append("")
    lines.append(f"Generated: {result['timestamp']}")
    lines.append(f"Total queries: {result['total_queries']}")
    lines.append("")

    agg = result["aggregate"]
    lines.append("## Aggregate Scores")
    lines.append("")
    lines.append("| Metric | Score |")
    lines.append("|--------|-------|")
    lines.append(f"| Claim Recall | {agg['claim_recall']:.3f} |")
    lines.append(f"| Citation Accuracy | {agg['citation_accuracy']:.3f} |")
    lines.append(f"| Independence Score | {agg['independence_score']:.3f} |")
    lines.append(
        f"| Adversary Catch Rate | {agg['adversary_catch_rate']:.3f} |"
    )
    lines.append(f"| Composite Score | {agg['composite_score']:.3f} |")
    lines.append("")

    baseline = result.get("baseline")
    regression = result.get("regression")
    if baseline and regression:
        lines.append("## Baseline Comparison")
        lines.append("")
        if regression["regressed"]:
            lines.append("**REGRESSION DETECTED**")
            lines.append("")
            for detail in regression["details"]:
                lines.append(
                    f"- {detail['metric']}: {detail['baseline']:.3f} → {detail['current']:.3f} "
                    f"(-{detail['diff']:.3f}, threshold {detail['threshold']})"
                )
        else:
            lines.append(
                "No regression detected (all metrics within 5% of baseline)."
            )
        lines.append("")

    lines.append("## Per-Query Results")
    lines.append("")
    for item in result["per_query"]:
        qid = item["query_id"]
        qtext = item["query_text"]
        cat = item["category"]
        scores = item["scores"]
        lines.append(f"### {qid} ({cat})")
        lines.append(f"{qtext}")
        lines.append("")
        lines.append(f"- Claim Recall: {scores['claim_recall']:.3f}")
        lines.append(f"- Citation Accuracy: {scores['citation_accuracy']:.3f}")
        lines.append(
            f"- Independence Score: {scores['independence_score']:.3f}"
        )
        lines.append(
            f"- Adversary Catch Rate: {scores['adversary_catch_rate']:.3f}"
        )
        lines.append(f"- Composite Score: {scores['composite_score']:.3f}")
        lines.append("")

    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI parser."""
    parser = argparse.ArgumentParser(
        prog="regression_runner",
        description="Run the research pipeline eval harness and compare against a baseline.",
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
