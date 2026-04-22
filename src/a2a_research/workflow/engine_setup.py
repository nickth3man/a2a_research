"""Workflow setup stages: preprocess, clarify, plan."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.models import (
    AgentRole,
    AgentStatus,
    ClaimState,
    ClaimVerification,
)
from a2a_research.progress import ProgressPhase
from a2a_research.workflow.agents import run_agent as _run_agent
from a2a_research.workflow.claims import should_abort_preprocessing
from a2a_research.workflow.coerce import coerce_claims, coerce_dag
from a2a_research.workflow.reports import abort_report, planner_failed_report
from a2a_research.workflow.status import emit_v2, set_status

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import (
        Claim,
        ClaimDAG,
        ResearchSession,
        WorkflowBudget,
    )

__all__ = ["run_setup_stages"]


async def run_setup_stages(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
) -> tuple[str, list[Claim], ClaimDAG, list[str]] | None:
    """Run preprocess, clarify, and plan stages.

    Returns ``None`` if the workflow should abort early. Otherwise
    returns ``(committed_interpretation, claims, dag, seed_queries)``.
    """

    # Preprocess
    preprocess_result = await _run_agent(
        session,
        client,
        AgentRole.PREPROCESSOR,
        {"query": query, "session_id": session.id},
    )
    if should_abort_preprocessing(preprocess_result):
        session.error = "Query classified as unanswerable or sensitive."
        set_status(
            session,
            AgentRole.PREPROCESSOR,
            AgentStatus.COMPLETED,
            "Aborted query.",
        )
        session.final_report = abort_report(query, session.error)
        return None

    sanitized_query = preprocess_result.get("sanitized_query", query)
    query_class = preprocess_result.get(
        "query_class",
        preprocess_result.get("class", "factual"),
    )
    domain_hints = preprocess_result.get("domain_hints", [])

    # Clarify
    clarify_result = await _run_agent(
        session,
        client,
        AgentRole.CLARIFIER,
        {
            "query": sanitized_query,
            "query_class": query_class,
            "session_id": session.id,
        },
    )
    committed_interpretation = clarify_result.get(
        "committed_interpretation", sanitized_query
    )

    # Plan
    emit_v2(
        session.id,
        AgentRole.PLANNER,
        ProgressPhase.STEP_STARTED,
        "planner_started",
    )
    set_status(
        session, AgentRole.PLANNER, AgentStatus.RUNNING, "Decomposing query…"
    )
    plan_result = await _run_agent(
        session,
        client,
        AgentRole.PLANNER,
        {
            "query": committed_interpretation,
            "domain_hints": domain_hints,
            "session_id": session.id,
        },
    )
    claims = coerce_claims(plan_result.get("claims", []))
    dag = coerce_dag(plan_result.get("claim_dag", {}), claims=claims)
    seed_queries = [
        str(q)
        for q in plan_result.get("seed_queries", [])
        if isinstance(q, str)
    ]

    if not claims:
        set_status(
            session,
            AgentRole.PLANNER,
            AgentStatus.FAILED,
            "No claims produced.",
        )
        session.error = "Planner failed to decompose query."
        session.final_report = planner_failed_report(query)
        return None

    set_status(
        session,
        AgentRole.PLANNER,
        AgentStatus.COMPLETED,
        f"Extracted {len(claims)} claim(s), "
        f"DAG: {len(dag.nodes)} nodes, {len(dag.edges)} edges.",
    )
    emit_v2(
        session.id,
        AgentRole.PLANNER,
        ProgressPhase.STEP_COMPLETED,
        "planner_completed",
    )

    # Initialize claim state
    claim_state = ClaimState(
        original_claims=claims,
        dag=dag,
        verification={},
        unresolved_claim_ids=[c.id for c in claims],
        stale_claim_ids=[],
        resolved_claim_ids=[],
    )
    for c in claims:
        claim_state.verification[c.id] = ClaimVerification(claim_id=c.id)
    claim_state.refresh_resolution_lists()
    session.claim_state = claim_state

    return committed_interpretation, claims, dag, seed_queries
