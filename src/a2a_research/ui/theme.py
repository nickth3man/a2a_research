"""UI color tokens (no Mesop dependency) for agent status and claim verdict styling.

Centralises hex values so :mod:`a2a_research.ui.components` stays readable and tests
can import colours without pulling in Mesop.
"""

from __future__ import annotations

from a2a_research.models import AgentStatus


def status_color(status: AgentStatus) -> str:
    if status == AgentStatus.COMPLETED:
        return "#16a34a"
    if status == AgentStatus.RUNNING:
        return "#d97706"
    if status == AgentStatus.FAILED:
        return "#dc2626"
    return "#9ca3af"


def verdict_color(verdict: str) -> str:
    if verdict == "SUPPORTED":
        return "#16a34a"
    if verdict == "REFUTED":
        return "#dc2626"
    return "#d97706"


def verdict_bg(verdict: str) -> str:
    if verdict == "SUPPORTED":
        return "#dcfce7"
    if verdict == "REFUTED":
        return "#fee2e2"
    return "#fef3c7"
