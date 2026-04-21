"""Planner step for the coordinator workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.models import AgentRole, AgentStatus
from a2a_research.progress import ProgressPhase
from a2a_research.workflow.coordinator_helpers import (
    coerce_claim,
    emit_role_event,
    payload,
    planner_failed_report,
    set_status,
    task_failed,
)

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import ResearchSession


async def run_planner_step(
    session: "ResearchSession", client: "A2AClient", query: str
) -> tuple[list, list[str], bool]:
    """Run planner and return (claims, seed_queries, should_abort)."""
    emit_role_event(
        session.id,
        AgentRole.PLANNER,
        ProgressPhase.STEP_STARTED,
        "planner_started",
    )
    set_status(
        session, AgentRole.PLANNER, AgentStatus.RUNNING, "Decomposing query…"
    )
    plan_task = await client.send(
        AgentRole.PLANNER,
        payload={"query": query, "session_id": session.id},
    )
    plan = payload(plan_task)
    plan_failed = task_failed(plan_task)
    claims = [
        c
        for c in (coerce_claim(item) for item in (plan.get("claims") or []))
        if c is not None
    ]
    seed_queries = [
        str(q) for q in (plan.get("seed_queries") or []) if isinstance(q, str)
    ]
    session.claims = claims
    set_status(
        session,
        AgentRole.PLANNER,
        AgentStatus.FAILED if plan_failed else AgentStatus.COMPLETED,
        (
            "Failed to decompose query."
            if plan_failed
            else f"Extracted {len(claims)} claim(s)."
        ),
    )
    if plan_failed:
        emit_role_event(
            session.id,
            AgentRole.PLANNER,
            ProgressPhase.STEP_FAILED,
            "planner_failed",
        )
        session.error = "Planner failed to decompose query."
        for role in (
            AgentRole.SEARCHER,
            AgentRole.READER,
            AgentRole.FACT_CHECKER,
            AgentRole.SYNTHESIZER,
        ):
            set_status(
                session, role, AgentStatus.FAILED, "Skipped: planner failed."
            )
        session.report = None
        session.final_report = planner_failed_report(query)
        return claims, seed_queries, True
    emit_role_event(
        session.id,
        AgentRole.PLANNER,
        ProgressPhase.STEP_COMPLETED,
        "planner_completed",
    )
    return claims, seed_queries, False
