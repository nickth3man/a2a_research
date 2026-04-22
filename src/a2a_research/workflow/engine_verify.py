"""Workflow verify and adversary stages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.a2a import A2AClient
    from a2a_research.models import (
        Claim,
        ClaimState,
        EvidenceUnit,
        IndependenceGraph,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )
    from a2a_research.tools import PageContent

from a2a_research.logging.app_logging import get_logger
from a2a_research.models import (
    AgentRole,
    ProvenanceEdgeType,
    ProvenanceNode,
    Verdict,
)
from a2a_research.workflow.agents import run_agent as _run_agent
from a2a_research.workflow.coerce import (
    coerce_claim_state,
    coerce_claims,
    coerce_follow_ups,
    coerce_replan_reasons,
    merge_verified_claims_into_state,
)
from a2a_research.workflow.provenance import (
    challenge_node_id,
    claim_node_id,
    ensure_edge,
    ensure_node,
    verdict_node_id,
)

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import (
        Claim,
        ClaimState,
        EvidenceUnit,
        IndependenceGraph,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )
    from a2a_research.tools import PageContent

logger = get_logger(__name__)

__all__ = ["run_verify"]


async def run_verify(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
    claim_state: ClaimState,
    to_process: list[Claim],
    pages: list[PageContent],
    deduped_new: list[EvidenceUnit],
    accumulated_evidence: list[EvidenceUnit],
    independence_graph: IndependenceGraph,
    provenance_tree: ProvenanceTree,
    _update_wall_seconds: Callable[[], None],
    _emit_budget: Callable[[str, AgentRole, str], None],
    loop_round: int,
) -> list[Any] | None:
    """Run verify and adversary stages.

    Returns ``None`` if the loop should break (budget exhausted).
    Otherwise returns ``replan_reasons``.
    """
    if not deduped_new:
        return []

    verify_result = await _run_agent(
        session,
        client,
        AgentRole.FACT_CHECKER,
        {
            "query": query,
            "claims": [c.model_dump(mode="json") for c in to_process],
            "claim_dag": claim_state.dag.model_dump(mode="json"),
            "evidence": [p.model_dump(mode="json") for p in pages],
            "new_evidence": [e.model_dump(mode="json") for e in deduped_new],
            "accumulated_evidence": [
                e.model_dump(mode="json") for e in accumulated_evidence
            ],
            "independence_graph": independence_graph.model_dump(mode="json"),
            "session_id": session.id,
        },
    )
    updated_state = coerce_claim_state(
        verify_result.get("updated_claim_state", {}),
        fallback_claims=claim_state.original_claims,
        fallback_dag=claim_state.dag,
    )
    if updated_state:
        claim_state = updated_state
    else:
        claim_state = merge_verified_claims_into_state(
            claim_state,
            coerce_claims(verify_result.get("verified_claims", [])),
            independence_graph,
        )
    claim_state.refresh_resolution_lists()
    session.claim_state = claim_state

    coerce_follow_ups(verify_result.get("claim_follow_ups", []))
    replan_reasons = coerce_replan_reasons(
        verify_result.get("replan_reasons", [])
    )
    session.replan_reasons = replan_reasons

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
        if claim is not None:
            ensure_edge(
                provenance_tree,
                claim_node_id(claim.id),
                verdict_node,
                ProvenanceEdgeType.PASSAGE_TO_VERDICT,
            )

    _update_wall_seconds()
    if session.budget_consumed.is_exhausted(budget):
        logger.info("Budget exhausted after verify in round %s", loop_round)
        _emit_budget(
            session.id,
            AgentRole.FACT_CHECKER,
            "budget_exhausted_after_verify",
        )
        return None

    # Adversary gate
    tentative = claim_state.tentatively_supported_claim_ids
    if tentative:
        adversary_result = await _run_agent(
            session,
            client,
            AgentRole.ADVERSARY,
            {
                "claims": [
                    c.model_dump(mode="json")
                    for c in claim_state.original_claims
                    if c.id in tentative
                ],
                "evidence": [
                    e.model_dump(mode="json") for e in accumulated_evidence
                ],
                "session_id": session.id,
            },
        )
        challenges = adversary_result.get("challenge_results", [])
        for ch in challenges:
            claim_id = ch.get("claim_id")
            result = ch.get("challenge_result", "HOLDS")
            v = claim_state.verification.get(claim_id)
            if v is not None:
                v.adversary_result = result
                if result == "REFUTED":
                    v.verdict = Verdict.REFUTED
                    claim_state.mark_dependents_stale(claim_id)
                elif result == "WEAKENED":
                    v.verdict = Verdict.MIXED
                ensure_node(
                    provenance_tree,
                    ProvenanceNode(
                        id=challenge_node_id(claim_id),
                        node_type="challenge",
                        ref_id=str(claim_id),
                        metadata={"challenge_result": result},
                    ),
                )
                ensure_edge(
                    provenance_tree,
                    verdict_node_id(str(claim_id)),
                    challenge_node_id(str(claim_id)),
                    ProvenanceEdgeType.PASSAGE_TO_ADVERSARY_CHALLENGE,
                )
        claim_state.refresh_resolution_lists()
        session.claim_state = claim_state

        _update_wall_seconds()
        if session.budget_consumed.is_exhausted(budget):
            logger.info(
                "Budget exhausted after adversary in round %s",
                loop_round,
            )
            _emit_budget(
                session.id,
                AgentRole.ADVERSARY,
                "budget_exhausted_after_adversary",
            )
            return None

    return replan_reasons
