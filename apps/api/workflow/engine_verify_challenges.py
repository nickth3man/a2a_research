"""Challenge application helpers for adversary stage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, cast

from core.models import (
    ProvenanceEdgeType,
    ProvenanceNode,
    Verdict,
)
from workflow.provenance import (
    challenge_node_id,
    ensure_edge,
    ensure_node,
    verdict_node_id,
)

if TYPE_CHECKING:
    from core import ClaimState, ProvenanceTree


def apply_challenges(
    claim_state: ClaimState,
    provenance_tree: ProvenanceTree,
    challenges: list[dict[str, Any]],
) -> None:
    for challenge in challenges:
        claim_id = str(challenge.get("claim_id") or "")
        raw_result = str(challenge.get("challenge_result") or "HOLDS")
        result = cast(
            "Literal['HOLDS', 'WEAKENED', 'REFUTED', 'NOT_RUN']",
            raw_result
            if raw_result in {"HOLDS", "WEAKENED", "REFUTED", "NOT_RUN"}
            else "HOLDS",
        )
        verification = claim_state.verification.get(claim_id)
        if verification is None:
            continue
        verification.adversary_result = result
        if result == "REFUTED":
            verification.verdict = Verdict.REFUTED
            claim_state.mark_dependents_stale(claim_id)
        elif result == "WEAKENED":
            verification.verdict = Verdict.MIXED
        ensure_node(
            provenance_tree,
            ProvenanceNode(
                id=challenge_node_id(claim_id),
                node_type="challenge",
                ref_id=claim_id,
                metadata={"challenge_result": result},
            ),
        )
        ensure_edge(
            provenance_tree,
            verdict_node_id(claim_id),
            challenge_node_id(claim_id),
            ProvenanceEdgeType.PASSAGE_TO_ADVERSARY_CHALLENGE,
        )
