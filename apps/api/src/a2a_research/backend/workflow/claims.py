"""Claim processing helpers for the workflow engine."""

from __future__ import annotations

from typing import Any

from a2a_research.backend.core.models import Claim, ClaimState, Verdict

__all__ = ["claims_to_process", "should_abort_preprocessing"]


def claims_to_process(claim_state: ClaimState) -> list[Claim]:
    """Unresolved + STALE claims, sorted by DAG topological order."""
    order = claim_state.dag.topological_order()
    if not order:
        order = [c.id for c in claim_state.original_claims]
    queue = []
    for claim_id in order:
        v = claim_state.verification.get(claim_id)
        if v is None:
            continue
        if v.verdict not in (Verdict.UNRESOLVED, Verdict.STALE):
            continue
        parents = claim_state.dag.parents_of(claim_id)
        if any(
            claim_state.verification.get(p)
            and claim_state.verification[p].verdict == Verdict.REFUTED
            for p in parents
        ):
            v.verdict = Verdict.STALE
            continue
        claim = next(
            (c for c in claim_state.original_claims if c.id == claim_id), None
        )
        if claim:
            queue.append(claim)
    return queue


def should_abort_preprocessing(result: dict[str, Any]) -> bool:
    query_class = result.get("query_class", "")
    confidence = float(
        result.get(
            "query_class_confidence", result.get("class_confidence", 0.0)
        )
    )
    return query_class == "unanswerable" and confidence > 0.8
