"""Helpers for the workflow evidence loop."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core import AgentRole, ProgressPhase
from core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from workflow import emit_envelope, emit_step
from workflow import run_agent as _run_agent
from workflow.coerce import (
    claims_from_state,
    coerce_report,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from core import A2AClient
    from core.models import (
        EvidenceUnit,
        ResearchSession,
        WorkflowBudget,
    )


def emit_budget_snapshot(
    session: ResearchSession,
    budget: WorkflowBudget,
    update_wall_seconds: Callable[[], None],
    session_id: str,
    role: AgentRole | None,
    label: str,
) -> None:
    update_wall_seconds()
    bc = session.budget_consumed
    detail = (
        f"rounds={bc.rounds}/{budget.max_rounds} "
        f"tokens={bc.tokens_consumed}/{budget.max_tokens} "
        f"wall_s={bc.wall_seconds:.1f}/{budget.max_wall_seconds:.0f} "
        f"http={bc.http_calls}/{budget.max_http_calls} "
        f"urls={bc.urls_fetched} "
        f"critic_loops={bc.critic_revision_loops}/"
        f"{budget.max_critic_revision_loops}"
    )
    emit_step(
        session_id,
        role,
        ProgressPhase.STEP_SUBSTEP,
        label,
        detail=detail,
    )


async def run_snapshot_stage(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
    accumulated_evidence: list[EvidenceUnit],
    update_wall_seconds: Callable[[], None],
    loop_round: int,
) -> bool:
    claim_state = session.claim_state
    if claim_state is None:
        return False
    snapshot_claims = claims_from_state(claim_state)
    snapshot_result = await _run_agent(
        session,
        client,
        AgentRole.SYNTHESIZER,
        {
            "query": query,
            "claims": [c.model_dump(mode="json") for c in snapshot_claims],
            "claim_state": claim_state.model_dump(mode="json"),
            "evidence": [
                e.model_dump(mode="json") for e in accumulated_evidence
            ],
            "mode": "tentative",
            "session_id": session.id,
            "trace_id": session.trace_id,
            "diagnostics": [
                e.model_dump(mode="json") for e in session.error_ledger
            ],
        },
    )
    snapshot_report = coerce_report(snapshot_result.get("report"))
    if snapshot_report:
        session.tentative_report = snapshot_report
    update_wall_seconds()
    if not session.budget_consumed.is_exhausted(budget):
        return True
    emit_envelope(
        session.id,
        ErrorEnvelope(
            role=AgentRole.SYNTHESIZER,
            code=ErrorCode.BUDGET_EXHAUSTED_AFTER_SNAPSHOT,
            severity=ErrorSeverity.DEGRADED,
            retryable=False,
            root_cause="Budget exhausted after tentative snapshot.",
            trace_id=session.trace_id,
        ),
        session,
    )
    return False
