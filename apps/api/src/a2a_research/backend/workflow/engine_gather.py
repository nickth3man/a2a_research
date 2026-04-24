"""Evidence gathering stages: search, rank, read, normalize."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        AgentRole,
        Claim,
        ClaimState,
        EvidenceUnit,
        IndependenceGraph,
        NoveltyTracker,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )
    from a2a_research.backend.tools import PageContent

from a2a_research.backend.workflow.engine_gather_normalize import (
    run_normalize_stage,
)
from a2a_research.backend.workflow.engine_gather_rank_read import (
    run_rank_stage,
    run_read_stage,
)
from a2a_research.backend.workflow.engine_gather_search import run_search_stage

__all__ = ["gather_evidence"]


async def gather_evidence(
    session: ResearchSession,
    client: A2AClient,
    budget: WorkflowBudget,
    claim_state: ClaimState,
    to_process: list[Claim],
    claim_queries: list[str],
    accumulated_evidence: list[EvidenceUnit],
    independence_graph: IndependenceGraph,
    provenance_tree: ProvenanceTree,
    novelty_tracker: NoveltyTracker,
    _update_wall_seconds: Callable[[], None],
    _emit_budget: Callable[[str, AgentRole, str], None],
    loop_round: int,
) -> tuple[list[EvidenceUnit], list[PageContent], list[EvidenceUnit]] | None:
    """Run search, rank, read, and normalize stages."""
    search_stage = await run_search_stage(
        session,
        client,
        budget,
        claim_state,
        claim_queries,
        _update_wall_seconds,
        _emit_budget,
        loop_round,
    )
    if search_stage is None:
        return None
    hits, search_back_channel = search_stage

    rank_stage = await run_rank_stage(
        session,
        client,
        budget,
        claim_state,
        to_process,
        hits,
        _update_wall_seconds,
        loop_round,
        search_back_channel,
    )
    if rank_stage is None:
        return None
    urls_to_fetch, rank_result = rank_stage

    read_stage = await run_read_stage(
        session,
        client,
        budget,
        to_process,
        urls_to_fetch,
        rank_result,
        _update_wall_seconds,
        _emit_budget,
        loop_round,
    )
    if read_stage is None:
        return None
    pages, read_result = read_stage

    deduped_new = await run_normalize_stage(
        session,
        client,
        budget,
        to_process,
        claim_queries,
        accumulated_evidence,
        independence_graph,
        provenance_tree,
        novelty_tracker,
        hits,
        pages,
        read_result,
        _update_wall_seconds,
        loop_round,
    )
    if deduped_new is None:
        return None
    return accumulated_evidence, pages, deduped_new
