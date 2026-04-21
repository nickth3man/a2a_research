"""Synthesizer step for the coordinator workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.models import AgentRole, AgentStatus
from a2a_research.progress import ProgressPhase
from a2a_research.workflow.coordinator_helpers import (
    coerce_report,
    emit_role_event,
    payload,
    set_status,
    task_failed,
)

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import Claim, ResearchSession, WebSource


async def run_synthesizer_step(
    session: "ResearchSession",
    client: "A2AClient",
    query: str,
    verified: list["Claim"],
    sources: list["WebSource"],
) -> bool:
    """Run synthesizer and return should_abort."""
    set_status(
        session, AgentRole.SYNTHESIZER, AgentStatus.RUNNING, "Writing report…"
    )
    emit_role_event(
        session.id,
        AgentRole.SYNTHESIZER,
        ProgressPhase.STEP_STARTED,
        "synthesizer_started",
    )
    syn_task = await client.send(
        AgentRole.SYNTHESIZER,
        payload={
            "session_id": session.id,
            "query": query,
            "verified_claims": [
                c.model_dump(mode="json") for c in (verified or session.claims)
            ],
            "sources": [s.model_dump(mode="json") for s in sources],
        },
        from_role=AgentRole.FACT_CHECKER,
    )
    syn_data = payload(syn_task)
    syn_failed = task_failed(syn_task)
    report = coerce_report(syn_data.get("report"))
    session.report = report
    session.final_report = report.to_markdown() if report else ""
    set_status(
        session,
        AgentRole.SYNTHESIZER,
        AgentStatus.FAILED if syn_failed else AgentStatus.COMPLETED,
        (
            "Failed to synthesize report."
            if syn_failed
            else "Report synthesized."
        ),
    )
    if syn_failed:
        emit_role_event(
            session.id,
            AgentRole.SYNTHESIZER,
            ProgressPhase.STEP_FAILED,
            "synthesizer_failed",
        )
        session.error = (
            session.error or "Synthesizer failed to produce a report."
        )
        return True
    emit_role_event(
        session.id,
        AgentRole.SYNTHESIZER,
        ProgressPhase.STEP_COMPLETED,
        "synthesizer_completed",
    )
    return False
