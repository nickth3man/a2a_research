"""Searcher step for the coordinator workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.models import AgentRole, AgentStatus
from a2a_research.progress import ProgressPhase
from a2a_research.workflow.coordinator_helpers import (
    coerce_web_hit,
    emit_role_event,
    error_report,
    payload,
    set_status,
    task_failed,
)

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import ResearchSession
    from a2a_research.tools import WebHit


async def run_searcher_step(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    seed_queries: list[str],
) -> tuple[list[WebHit], list[str], bool]:
    """Run searcher and return (hits, search_errors, should_abort)."""
    set_status(session, AgentRole.SEARCHER, AgentStatus.RUNNING, "Searching…")
    emit_role_event(
        session.id,
        AgentRole.SEARCHER,
        ProgressPhase.STEP_STARTED,
        "searcher_started",
    )
    search_task = await client.send(
        AgentRole.SEARCHER,
        payload={"queries": seed_queries, "session_id": session.id},
        from_role=AgentRole.PLANNER,
    )
    search_data = payload(search_task)
    search_failed = task_failed(search_task)
    raw_hits = search_data.get("hits") or []
    hits_maybe = [coerce_web_hit(h) for h in raw_hits]
    hits: list[WebHit] = [h for h in hits_maybe if h is not None]
    search_errors = [
        str(e) for e in (search_data.get("errors") or []) if isinstance(e, str)
    ]

    if search_failed or not hits:
        reason = " | ".join(search_errors) or "web search produced no results."
        set_status(
            session,
            AgentRole.SEARCHER,
            AgentStatus.FAILED,
            f"Search failed: {reason}",
        )
        for role in (
            AgentRole.READER,
            AgentRole.FACT_CHECKER,
            AgentRole.SYNTHESIZER,
        ):
            msg = (
                "Skipped: search failed."
                if role == AgentRole.READER
                else "Skipped: no verified evidence to synthesize."
                if role == AgentRole.SYNTHESIZER
                else "Skipped: no evidence."
            )
            set_status(session, role, AgentStatus.FAILED, msg)
        emit_role_event(
            session.id,
            AgentRole.SEARCHER,
            ProgressPhase.STEP_FAILED,
            "searcher_failed",
        )
        session.error = "Research pipeline aborted: " + reason
        session.final_report = error_report(query, reason, search_errors)
        return hits, search_errors, True

    urls = [h.url for h in hits[:6]]
    set_status(
        session,
        AgentRole.SEARCHER,
        AgentStatus.COMPLETED,
        f"{len(hits)} hit(s), {len(urls)} URL(s) selected.",
    )
    emit_role_event(
        session.id,
        AgentRole.SEARCHER,
        ProgressPhase.STEP_COMPLETED,
        "searcher_completed",
    )
    return hits, search_errors, False
