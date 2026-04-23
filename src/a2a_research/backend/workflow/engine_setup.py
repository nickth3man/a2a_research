"""Workflow setup stages: preprocess, clarify, plan."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.backend.core.models import (
    AgentRole,
    AgentStatus,
    ClaimState,
    ClaimVerification,
)
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.core.progress import ProgressPhase
from a2a_research.backend.workflow.agents import run_agent as _run_agent
from a2a_research.backend.workflow.claims import should_abort_preprocessing
from a2a_research.backend.workflow.coerce import coerce_claims, coerce_dag
from a2a_research.backend.workflow.reports import (
    abort_report,
    planner_failed_report,
)
from a2a_research.backend.workflow.status import (
    emit_envelope,
    emit_step,
    set_status,
)

if TYPE_CHECKING:
    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
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

    # ── Preprocess ──────────────────────────────────────────────────
    preprocess_result = await _run_agent(
        session,
        client,
        AgentRole.PREPROCESSOR,
        {
            "query": query,
            "session_id": session.id,
            "trace_id": session.trace_id,
        },
    )

    # Emit warning envelope for any partial-failure flags from PRE
    if preprocess_result.get("warning"):
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.PREPROCESSOR,
                code=ErrorCode.QUERY_REJECTED,
                severity=ErrorSeverity.WARNING,
                retryable=False,
                root_cause=str(preprocess_result.get("warning", "")),
                trace_id=session.trace_id,
            ),
            session,
        )

    if should_abort_preprocessing(preprocess_result):
        envelope = ErrorEnvelope(
            role=AgentRole.PREPROCESSOR,
            code=ErrorCode.QUERY_REJECTED,
            severity=ErrorSeverity.FATAL,
            retryable=False,
            root_cause="Query classified as unanswerable or sensitive.",
            trace_id=session.trace_id,
        )
        emit_envelope(session.id, envelope, session)
        session.error = "Query classified as unanswerable or sensitive."
        set_status(
            session,
            AgentRole.PREPROCESSOR,
            AgentStatus.COMPLETED,
            "Aborted query.",
        )
        session.final_report = abort_report(query, session.error)
        emit_step(
            session.id,
            None,
            ProgressPhase.FINAL_DIAGNOSTICS,
            "abort_report",
            detail=f"error_count={len(session.error_ledger)}",
        )
        return None

    sanitized_query = preprocess_result.get("sanitized_query", query)
    query_class = preprocess_result.get(
        "query_class",
        preprocess_result.get("class", "factual"),
    )
    domain_hints = preprocess_result.get("domain_hints", [])

    # ── Clarify (back-channel: PRE→CLR) ─────────────────────────────
    clarify_result = await _run_agent(
        session,
        client,
        AgentRole.CLARIFIER,
        {
            "query": sanitized_query,
            "query_class": query_class,
            "session_id": session.id,
            "trace_id": session.trace_id,
            # Back-channel from PRE
            "normalization_rationale": preprocess_result.get(
                "normalization_notes", ""
            ),
            "risky_spans": preprocess_result.get("risky_spans", []),
            "domain_hints": domain_hints,
        },
    )
    committed_interpretation = clarify_result.get(
        "committed_interpretation", sanitized_query
    )

    # ── Plan (back-channel: CLR→PLN) ─────────────────────────────────
    emit_step(
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
            "trace_id": session.trace_id,
            # Back-channel from CLR
            "ambiguity_constraints": clarify_result.get(
                "ambiguity_notes", ""
            ),
            "interpretation_rationale": clarify_result.get(
                "rejected_interpretations", []
            ),
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
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.PLANNER,
                code=ErrorCode.PLANNER_EMPTY,
                severity=ErrorSeverity.FATAL,
                retryable=False,
                root_cause="Planner produced no claims.",
                trace_id=session.trace_id,
            ),
            session,
        )
        set_status(
            session,
            AgentRole.PLANNER,
            AgentStatus.FAILED,
            "No claims produced.",
        )
        session.error = "Planner failed to decompose query."
        session.final_report = planner_failed_report(query)
        emit_step(
            session.id,
            None,
            ProgressPhase.FINAL_DIAGNOSTICS,
            "planner_failed",
            detail=f"error_count={len(session.error_ledger)}",
        )
        return None

    # Warn if claim coverage is thin
    min_claims = getattr(budget, "min_claims_threshold", 2)
    if len(claims) < min_claims:
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.PLANNER,
                code=ErrorCode.LOW_CLAIM_COVERAGE,
                severity=ErrorSeverity.WARNING,
                retryable=True,
                root_cause=f"Planner produced only {len(claims)} claim(s).",
                trace_id=session.trace_id,
            ),
            session,
        )

    set_status(
        session,
        AgentRole.PLANNER,
        AgentStatus.COMPLETED,
        f"Extracted {len(claims)} claim(s), "
        f"DAG: {len(dag.nodes)} nodes, {len(dag.edges)} edges.",
    )
    emit_step(
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
