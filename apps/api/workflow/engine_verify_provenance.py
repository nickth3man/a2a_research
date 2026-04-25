"""Provenance helpers for verification stages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core import get_logger
from core.models import (
    AgentRole,
    ProvenanceEdgeType,
    ProvenanceNode,
)
from core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from workflow import emit_envelope
from workflow.provenance import (
    claim_node_id,
    ensure_edge,
    ensure_node,
    verdict_node_id,
)

if TYPE_CHECKING:
    from core.models import (
        ClaimState,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )

logger = get_logger(__name__)


def update_verdict_provenance(
    claim_state: ClaimState,
    provenance_tree: ProvenanceTree,
) -> None:
    for verification in claim_state.verification.values():
        verdict_node = verdict_node_id(verification.claim_id)
        ensure_node(
            provenance_tree,
            ProvenanceNode(
                id=verdict_node,
                node_type="verdict",
                ref_id=verification.claim_id,
                metadata={
                    "verdict": verification.verdict.value,
                    "confidence": verification.confidence,
                },
            ),
        )
        claim = claim_state.get_claim(verification.claim_id)
        if claim is None:
            continue
        ensure_edge(
            provenance_tree,
            claim_node_id(claim.id),
            verdict_node,
            ProvenanceEdgeType.PASSAGE_TO_VERDICT,
        )


def verify_budget_remaining(
    session: ResearchSession,
    budget: WorkflowBudget,
    loop_round: int,
) -> bool:
    if not session.budget_consumed.is_exhausted(budget):
        return True
    logger.info("Budget exhausted after verify in round %s", loop_round)
    emit_envelope(
        session.id,
        ErrorEnvelope(
            role=AgentRole.FACT_CHECKER,
            code=ErrorCode.BUDGET_EXHAUSTED_AFTER_VERIFY,
            severity=ErrorSeverity.DEGRADED,
            retryable=False,
            root_cause="Budget exhausted after fact-check.",
            trace_id=session.trace_id,
        ),
        session,
    )
    return False
