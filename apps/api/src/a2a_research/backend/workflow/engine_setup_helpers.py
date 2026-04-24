"""Helpers for workflow setup stages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from a2a_research.backend.core.models import (
    AgentRole,
    AgentStatus,
    Claim,
    ClaimDAG,
    ClaimState,
    ClaimVerification,
)
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.core.progress import ProgressPhase
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
    from a2a_research.backend.core.models import ResearchSession


def emit_preprocess_warning(
    session: ResearchSession,
    preprocess_result: dict[str, Any],
) -> None:
    warning = preprocess_result.get("warning")
    if not warning:
        return
    emit_envelope(
        session.id,
        ErrorEnvelope(
            role=AgentRole.PREPROCESSOR,
            code=ErrorCode.QUERY_REJECTED,
            severity=ErrorSeverity.WARNING,
            retryable=False,
            root_cause=str(warning),
            trace_id=session.trace_id,
        ),
        session,
    )


def abort_for_preprocessing(session: ResearchSession, query: str) -> None:
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


def fail_for_empty_plan(session: ResearchSession, query: str) -> None:
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


def warn_for_low_claim_coverage(
    session: ResearchSession,
    claim_count: int,
    min_claims: int,
) -> None:
    if claim_count >= min_claims:
        return
    emit_envelope(
        session.id,
        ErrorEnvelope(
            role=AgentRole.PLANNER,
            code=ErrorCode.LOW_CLAIM_COVERAGE,
            severity=ErrorSeverity.WARNING,
            retryable=True,
            root_cause=f"Planner produced only {claim_count} claim(s).",
            trace_id=session.trace_id,
        ),
        session,
    )


def finalize_plan(
    session: ResearchSession,
    claims: list[Claim],
    dag: ClaimDAG,
) -> None:
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


def initialize_claim_state(
    session: ResearchSession,
    claims: list[Claim],
    dag: ClaimDAG,
) -> None:
    claim_state = ClaimState(
        original_claims=claims,
        dag=dag,
        verification={},
        unresolved_claim_ids=[c.id for c in claims],
        stale_claim_ids=[],
        resolved_claim_ids=[],
    )
    for claim in claims:
        claim_state.verification[claim.id] = ClaimVerification(
            claim_id=claim.id
        )
    claim_state.refresh_resolution_lists()
    session.claim_state = claim_state
