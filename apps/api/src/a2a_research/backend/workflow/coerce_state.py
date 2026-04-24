"""Claim-state coercion and merge helpers."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from a2a_research.backend.core.models import (
    Claim,
    ClaimDAG,
    ClaimState,
    ClaimVerification,
    IndependenceGraph,
    Verdict,
)

__all__ = [
    "claims_from_state",
    "coerce_claim_state",
    "merge_verified_claims_into_state",
]


def coerce_claim_state(
    raw: Any,
    *,
    fallback_claims: list[Claim] | None = None,
    fallback_dag: ClaimDAG | None = None,
) -> ClaimState | None:
    if isinstance(raw, ClaimState):
        state = raw
    elif isinstance(raw, dict):
        if not raw:
            return None
        try:
            state = ClaimState.model_validate(raw)
        except ValidationError:
            state = None
    else:
        state = None
    if state is None:
        return None
    if fallback_claims and not state.original_claims:
        state.original_claims = fallback_claims
    if fallback_dag and not state.dag.nodes and not state.dag.edges:
        state.dag = fallback_dag
    state.refresh_resolution_lists()
    return state


def claims_from_state(claim_state: ClaimState) -> list[Claim]:
    """Return original claims with their verification verdicts merged in."""
    result: list[Claim] = []
    for claim in claim_state.original_claims:
        v = claim_state.verification.get(claim.id)
        if v is not None:
            sources = v.supporting_evidence_ids or claim.sources
            claim = claim.model_copy(
                update={
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    "sources": sources,
                }
            )
        result.append(claim)
    return result


def merge_verified_claims_into_state(
    claim_state: ClaimState,
    verified_claims: list[Claim],
    independence_graph: IndependenceGraph,
) -> ClaimState:
    if not verified_claims:
        return claim_state
    for verified in verified_claims:
        verification = claim_state.verification.get(verified.id)
        if verification is None:
            verification = ClaimVerification(claim_id=verified.id)
            claim_state.verification[verified.id] = verification
        verification.verdict = verified.verdict
        verification.confidence = verified.confidence
        verification.independent_source_count = (
            independence_graph.independent_source_count(verified.id)
        )
        verification.supporting_evidence_ids = list(verified.sources)
        if verified.verdict == Verdict.REFUTED:
            claim_state.mark_dependents_stale(verified.id)
    claim_state.refresh_resolution_lists()
    return claim_state
