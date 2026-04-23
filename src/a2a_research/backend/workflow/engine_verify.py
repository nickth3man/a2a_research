"""Workflow verify and adversary stages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        Claim,
        ClaimState,
        EvidenceUnit,
        IndependenceGraph,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )
    from a2a_research.backend.tools import PageContent

from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.progress import ProgressPhase
from a2a_research.backend.workflow.agents import run_agent as _run_agent
from a2a_research.backend.workflow.coerce import (
    coerce_claim_state,
    coerce_claims,
    coerce_follow_ups,
    coerce_replan_reasons,
    merge_verified_claims_into_state,
)
from a2a_research.backend.workflow.engine_verify_adversary import (
    run_adversary_stage,
)
from a2a_research.backend.workflow.engine_verify_provenance import (
    update_verdict_provenance,
    verify_budget_remaining,
)
from a2a_research.backend.workflow.status import emit_step

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

    # ── Fact-check (back-channel: DAG + extraction confidence) ───────
    emit_step(
        session.id,
        AgentRole.FACT_CHECKER,
        ProgressPhase.STEP_STARTED,
        "verifying_claims",
    )
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
            "trace_id": session.trace_id,
            # extraction confidence from reader (if provided upstream)
            "extraction_confidence": {
                getattr(p, "url", ""): getattr(p, "confidence", 1.0)
                for p in pages
            },
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

    update_verdict_provenance(claim_state, provenance_tree)

    _update_wall_seconds()
    if not verify_budget_remaining(session, budget, loop_round):
        return None

    if not await run_adversary_stage(
        session,
        client,
        budget,
        claim_state,
        accumulated_evidence,
        provenance_tree,
        verify_result,
        _update_wall_seconds,
        loop_round,
    ):
        return None

    return replan_reasons
