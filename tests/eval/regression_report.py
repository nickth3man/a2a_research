"""Markdown report generation for regression evaluation."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


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
    """Compare current scores against baseline and flag regressions > 5%."""
    threshold = 0.05
    details: list[dict[str, Any]] = []
    regressed = False

    for key in current:
        if key not in baseline:
            continue
        diff = baseline[key] - current[key]
        if diff > threshold:
            regressed = True
            details.append(
                {
                    "metric": key,
                    "baseline": baseline[key],
                    "current": current[key],
                    "diff": diff,
                    "threshold": threshold,
                }
            )

    return {"regressed": regressed, "details": details}


def generate_markdown_report(result: dict[str, Any]) -> str:
    """Generate a markdown report from evaluation results."""
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
                    f"- {detail['metric']}: {detail['baseline']:.3f} →"
                    f" {detail['current']:.3f} "
                    f"(-{detail['diff']:.3f}, threshold"
                    f" {detail['threshold']})"
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
