"""Workflow replan stage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.a2a import A2AClient
    from a2a_research.models import (
        ClaimState,
        ResearchSession,
        WorkflowBudget,
    )

from a2a_research.models import AgentRole
from a2a_research.workflow.agents import run_agent as _run_agent

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import (
        ClaimState,
        ResearchSession,
        WorkflowBudget,
    )

__all__ = ["run_replan"]


async def run_replan(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    claim_state: ClaimState,
    replan_reasons: list[Any],
    budget: WorkflowBudget,
    _update_wall_seconds: Callable[[], None],
) -> None:
    """Run replan stage."""
    from a2a_research.models import ClaimVerification
    from a2a_research.workflow.coerce import coerce_claims, coerce_dag

    replan_result = await _run_agent(
        session,
        client,
        AgentRole.PLANNER,
        {
            "original_query": query,
            "current_claims": [
                c.model_dump(mode="json") for c in claim_state.original_claims
            ],
            "current_dag": claim_state.dag.model_dump(mode="json"),
            "replan_reasons": [
                r.model_dump(mode="json") for r in replan_reasons
            ],
            "mode": "surgical",
            "session_id": session.id,
        },
    )
    revised_claims = coerce_claims(
        replan_result.get("revised_claims", replan_result.get("claims", []))
    )
    revised_dag = coerce_dag(
        replan_result.get("revised_dag", replan_result.get("claim_dag", {})),
        claims=revised_claims,
    )
    if revised_claims:
        claim_state.original_claims = revised_claims
        claim_state.dag = revised_dag
        for c in revised_claims:
            if c.id not in claim_state.verification:
                claim_state.verification[c.id] = ClaimVerification(
                    claim_id=c.id
                )
        claim_state.refresh_resolution_lists()
        session.claim_state = claim_state
    _update_wall_seconds()
