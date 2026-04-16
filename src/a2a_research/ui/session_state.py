"""Pure UI session helpers (no Mesop imports) for testability and state rules.

``has_results`` mirrors the UI's notion of "pipeline finished enough to show output":
either all agents are terminal (completed/failed) or a non-empty ``final_report`` exists.
"""

from __future__ import annotations

from a2a_research.models import AgentStatus, ResearchSession


def has_results(session: ResearchSession) -> bool:
    """True when the session has a complete-enough agent view or a final report."""
    if not session.agent_results:
        return False
    return all(
        r.status in (AgentStatus.COMPLETED, AgentStatus.FAILED)
        for r in session.agent_results.values()
    ) or bool(session.final_report)


def has_progress(session: ResearchSession) -> bool:
    return bool(session.agent_results)


def get_session_error(session: ResearchSession) -> str | None:
    return session.error
