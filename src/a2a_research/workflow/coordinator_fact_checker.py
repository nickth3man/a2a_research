"""Fact checker step for the coordinator workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.models import AgentRole, AgentStatus
from a2a_research.progress import ProgressPhase
from a2a_research.workflow.coordinator_helpers import (
    coerce_claim,
    emit_role_event,
    error_report,
    payload,
    set_status,
    task_failed,
)

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import Claim, ResearchSession, WebSource
    from a2a_research.tools import PageContent


async def run_fact_checker_step(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    claims: list[Claim],
    successful_pages: list[PageContent],
    sources: list[WebSource],
) -> tuple[list[Claim], bool]:
    """Run fact checker and return (verified_claims, should_abort)."""
    set_status(
        session,
        AgentRole.FACT_CHECKER,
        AgentStatus.RUNNING,
        "Verifying claims…",
    )
    emit_role_event(
        session.id,
        AgentRole.FACT_CHECKER,
        ProgressPhase.STEP_STARTED,
        "fact_checker_started",
    )
    fc_task = await client.send(
        AgentRole.FACT_CHECKER,
        payload={
            "session_id": session.id,
            "query": query,
            "claims": [c.model_dump(mode="json") for c in claims],
            "evidence": [p.model_dump(mode="json") for p in successful_pages],
            "sources": [s.model_dump(mode="json") for s in sources],
        },
        from_role=AgentRole.READER,
    )
    fc_data = payload(fc_task)
    verified = [
        c
        for c in (
            coerce_claim(item)
            for item in (fc_data.get("verified_claims") or [])
        )
        if c is not None
    ]
    fc_failed = task_failed(fc_task)

    session.claims = verified or claims
    session.sources = sources

    if fc_failed:
        emit_role_event(
            session.id,
            AgentRole.FACT_CHECKER,
            ProgressPhase.STEP_FAILED,
            "fact_checker_failed",
        )
        set_status(
            session,
            AgentRole.FACT_CHECKER,
            AgentStatus.FAILED,
            "Failed to verify claims.",
        )
        set_status(
            session,
            AgentRole.SYNTHESIZER,
            AgentStatus.FAILED,
            "Skipped: verification failed.",
        )
        session.error = "FactChecker failed to verify claims."
        session.report = None
        session.final_report = error_report(query, "FactChecker failed.", [])
        return verified, True

    set_status(
        session,
        AgentRole.FACT_CHECKER,
        AgentStatus.COMPLETED,
        f"Verified {len(verified)} claim(s).",
    )
    emit_role_event(
        session.id,
        AgentRole.FACT_CHECKER,
        ProgressPhase.STEP_COMPLETED,
        "fact_checker_completed",
    )
    return verified, False
