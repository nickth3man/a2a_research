"""Workflow claim-centric evidence loop."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.models import (
    AgentRole,
    ClaimState,
    IndependenceGraph,
    NoveltyTracker,
    ProvenanceTree,
)
from a2a_research.backend.core.progress import ProgressPhase
from a2a_research.backend.workflow.agents import run_agent as _run_agent
from a2a_research.backend.workflow.claims import claims_to_process
from a2a_research.backend.workflow.engine_gather import gather_evidence
from a2a_research.backend.workflow.engine_replan import run_replan
from a2a_research.backend.workflow.engine_verify import run_verify
from a2a_research.backend.workflow.status import emit_v2

if TYPE_CHECKING:
    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        EvidenceUnit,
        ResearchSession,
        WorkflowBudget,
    )

logger = get_logger(__name__)

__all__ = ["run_evidence_loop"]


async def run_evidence_loop(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
    workflow_start: float,
    claim_state: ClaimState,
    seed_queries: list[str],
) -> tuple[ClaimState, list[EvidenceUnit], ProvenanceTree]:
    """Run the claim-centric evidence gathering loop."""

    def _update_wall_seconds() -> None:
        session.budget_consumed.wall_seconds = perf_counter() - workflow_start

    def _emit_budget(
        session_id: str, role: AgentRole | None, label: str
    ) -> None:
        _update_wall_seconds()
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
        emit_v2(
            session_id,
            role,
            ProgressPhase.STEP_SUBSTEP,
            label,
            detail=detail,
        )

    accumulated_evidence: list[EvidenceUnit] = []
    independence_graph = IndependenceGraph()
    provenance_tree = ProvenanceTree()
    novelty_tracker = NoveltyTracker()
    loop_round = 0
    previous_round_marginal_gain: int | None = None
    claim_queries = list(dict.fromkeys(seed_queries))

    while True:
        loop_round += 1
        session.budget_consumed.rounds = loop_round
        _update_wall_seconds()

        novelty_tracker = NoveltyTracker()
        session.novelty_tracker = novelty_tracker

        if claim_state.all_resolved:
            logger.info("All claims resolved after %s rounds", loop_round)
            break
        if session.budget_consumed.is_exhausted(budget):
            logger.info("Budget exhausted after %s rounds", loop_round)
            _emit_budget(session.id, None, "budget_exhausted")
            break
        if (
            previous_round_marginal_gain is not None
            and previous_round_marginal_gain < budget.min_marginal_evidence
        ):
            logger.info("Novelty below threshold after %s rounds", loop_round)
            break

        to_process = claims_to_process(claim_state)
        if not to_process:
            logger.info("No claims to process in round %s", loop_round)
            break

        _emit_budget(
            session.id, AgentRole.SEARCHER, f"round_{loop_round}_start"
        )
        emit_v2(
            session.id,
            AgentRole.SEARCHER,
            ProgressPhase.STEP_STARTED,
            f"evidence_gathering_round_{loop_round}",
            detail=f"claims={len(to_process)}",
        )

        gather_result = await gather_evidence(
            session,
            client,
            budget,
            claim_state,
            to_process,
            claim_queries,
            accumulated_evidence,
            independence_graph,
            provenance_tree,
            novelty_tracker,
            _update_wall_seconds,
            _emit_budget,
            loop_round,
        )
        if gather_result is None:
            break
        accumulated_evidence, pages, deduped_new = gather_result

        # Verify
        replan_reasons = await run_verify(
            session,
            client,
            query,
            budget,
            claim_state,
            to_process,
            pages,
            deduped_new,
            accumulated_evidence,
            independence_graph,
            provenance_tree,
            _update_wall_seconds,
            _emit_budget,
            loop_round,
        )
        if replan_reasons is None:
            break

        # Snapshot
        snapshot_result = await _run_agent(
            session,
            client,
            AgentRole.SYNTHESIZER,
            {
                "query": query,
                "claim_state": claim_state.model_dump(mode="json"),
                "evidence": [
                    e.model_dump(mode="json") for e in accumulated_evidence
                ],
                "mode": "tentative",
                "session_id": session.id,
            },
        )
        from a2a_research.backend.workflow.coerce import coerce_report

        snapshot_report = coerce_report(snapshot_result.get("report"))
        if snapshot_report:
            session.tentative_report = snapshot_report
        _update_wall_seconds()

        if session.budget_consumed.is_exhausted(budget):
            logger.info(
                "Budget exhausted after snapshot in round %s", loop_round
            )
            _emit_budget(
                session.id,
                AgentRole.SYNTHESIZER,
                "budget_exhausted_after_snapshot",
            )
            break

        # Replan check
        if replan_reasons and loop_round < budget.max_rounds:
            await run_replan(
                session,
                client,
                query,
                claim_state,
                replan_reasons,
                budget,
                _update_wall_seconds,
            )

        deduplicated_follow_ups = (
            list(dict.fromkeys(claim_queries)) if claim_queries else []
        )
        if not deduplicated_follow_ups and claim_state.all_resolved:
            break
        if not deduplicated_follow_ups and not claim_state.all_resolved:
            logger.info(
                "No follow-up queries remaining in round %s", loop_round
            )
            break

        previous_round_marginal_gain = novelty_tracker.marginal_gain
        _emit_budget(session.id, None, f"round_{loop_round}_end")

    return claim_state, accumulated_evidence, provenance_tree
