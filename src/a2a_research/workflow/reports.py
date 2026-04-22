"""Report generation helpers for workflow failure cases."""

from __future__ import annotations

__all__ = ["abort_report", "planner_failed_report"]


def planner_failed_report(query: str) -> str:
    return "\n".join(
        [
            "# Planner failed",
            "",
            f"**Query:** {query}",
            "",
            "The planner could not decompose this query into claims, "
            "so the pipeline stopped.",
            "",
        ]
    )


def abort_report(query: str, reason: str) -> str:
    return "\n".join(
        [
            "# Research unavailable",
            "",
            f"**Query:** {query}",
            "",
            reason,
            "",
        ]
    )
