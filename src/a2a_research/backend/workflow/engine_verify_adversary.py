"""Adversary-stage helpers for verification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.workflow.agents import run_agent as _run_agent
from a2a_research.backend.workflow.engine_verify_challenges import (
    apply_challenges,
)
from a2a_research.backend.workflow.engine_verify_counter import (
    collect_counter_evidence,
)
from a2a_research.backend.workflow.status import emit_envelope

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        ClaimState,
        EvidenceUnit,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )


async def run_adversary_stage(
    session: ResearchSession,
    client: A2AClient,
    budget: WorkflowBudget,
    claim_state: ClaimState,
    accumulated_evidence: list[EvidenceUnit],
    provenance_tree: ProvenanceTree,
    verify_result: dict[str, Any],
    update_wall_seconds: Callable[[], None],
    loop_round: int,
) -> bool:
    tentative = claim_state.tentatively_supported_claim_ids
    if not tentative:
        return True
    adv_payload: dict[str, Any] = {
        "claims": [
            c.model_dump(mode="json")
            for c in claim_state.original_claims
            if c.id in tentative
        ],
        "evidence": [e.model_dump(mode="json") for e in accumulated_evidence],
        "session_id": session.id,
        "trace_id": session.trace_id,
        "vulnerable_claims": verify_result.get("vulnerable_claims", []),
        "confidence_breakdown": {
            v.claim_id: v.confidence
            for v in claim_state.verification.values()
            if v.claim_id in tentative
        },
    }
    if not await collect_counter_evidence(
        session,
        client,
        budget,
        verify_result.get("counter_queries", []),
        adv_payload,
        update_wall_seconds,
    ):
        return False
    adversary_result = await _run_agent(
        session,
        client,
        AgentRole.ADVERSARY,
        adv_payload,
    )
    apply_challenges(
        claim_state,
        provenance_tree,
        cast(
            list[dict[str, Any]], adversary_result.get("challenge_results", [])
        ),
    )
    claim_state.refresh_resolution_lists()
    session.claim_state = claim_state
    update_wall_seconds()
    if not session.budget_consumed.is_exhausted(budget):
        return True
    emit_envelope(
        session.id,
        ErrorEnvelope(
            role=AgentRole.ADVERSARY,
            code=ErrorCode.BUDGET_EXHAUSTED_AFTER_VERIFY,
            severity=ErrorSeverity.DEGRADED,
            retryable=False,
            root_cause="Budget exhausted after adversary.",
            trace_id=session.trace_id,
        ),
        session,
    )
    return False
