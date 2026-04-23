"""Evidence gathering stages: search, rank, read, normalize."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
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

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.workflow.agents import run_agent as _run_agent
from a2a_research.backend.workflow.coerce import (
    coerce_evidence_unit,
    coerce_page_content,
    coerce_web_hit,
)
from a2a_research.backend.workflow.engine_provenance import update_provenance
from a2a_research.backend.workflow.status import emit_envelope

if TYPE_CHECKING:
    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        Claim,
        ClaimState,
        EvidenceUnit,
        IndependenceGraph,
        NoveltyTracker,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )
    from a2a_research.backend.tools import PageContent, WebHit

logger = get_logger(__name__)

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
    """Run search, rank, read, and normalize stages.

    Returns ``(new_accumulated_evidence, pages, deduped_new)`` or
    ``None`` if the loop should break.
    """

    # ── Search ───────────────────────────────────────────────────────
    search_result = await _run_agent(
        session,
        client,
        AgentRole.SEARCHER,
        {
            "queries": claim_queries,
            "freshness_hints": claim_state.freshness_windows,
            "session_id": session.id,
            "trace_id": session.trace_id,
        },
    )
    raw_hits = search_result.get("hits", [])
    hits_maybe = [coerce_web_hit(h) for h in raw_hits]
    hits: list[WebHit] = [h for h in hits_maybe if h is not None]
    _update_wall_seconds()

    if not hits:
        logger.warning("No search hits in round %s", loop_round)
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.SEARCHER,
                code=ErrorCode.NO_HITS,
                severity=ErrorSeverity.DEGRADED,
                retryable=True,
                root_cause=f"Search returned no hits in round {loop_round}.",
                partial_results={
                    "attempted_queries": claim_queries,
                    "round": loop_round,
                },
                trace_id=session.trace_id,
            ),
            session,
        )
        return None

    if session.budget_consumed.is_exhausted(budget):
        logger.info("Budget exhausted after search in round %s", loop_round)
        _emit_budget(
            session.id,
            AgentRole.SEARCHER,
            "budget_exhausted_after_search",
        )
        return None

    # ── Rank (back-channel: SEA→RNK) ─────────────────────────────────
    rank_result = await _run_agent(
        session,
        client,
        AgentRole.RANKER,
        {
            "hits": [h.model_dump(mode="json") for h in hits],
            "unresolved_claims": [
                c.model_dump(mode="json") for c in to_process
            ],
            "freshness_windows": {
                k: v.model_dump(mode="json")
                for k, v in claim_state.freshness_windows.items()
            },
            "session_id": session.id,
            "trace_id": session.trace_id,
            # Back-channel from SEA
            "source_trust_priors": search_result.get(
                "source_trust_priors", {}
            ),
            "duplicate_domain_hints": search_result.get(
                "duplicate_domain_hints", []
            ),
        },
    )
    ranked_urls = [str(u) for u in rank_result.get("ranked_urls", [])]
    fetch_budget = min(
        budget.max_urls_fetched - session.budget_consumed.urls_fetched,
        8,
    )
    urls_to_fetch = ranked_urls[:fetch_budget]
    _update_wall_seconds()

    if not urls_to_fetch:
        logger.warning(
            "No URLs to fetch after ranking in round %s", loop_round
        )
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.RANKER,
                code=ErrorCode.ALL_URLS_FILTERED,
                severity=ErrorSeverity.DEGRADED,
                retryable=True,
                root_cause=(
                    f"All URLs filtered by ranker in round {loop_round}."
                ),
                trace_id=session.trace_id,
            ),
            session,
        )
        return None

    # ── Read (back-channel: RNK→REA) ─────────────────────────────────
    read_result = await _run_agent(
        session,
        client,
        AgentRole.READER,
        {
            "urls": urls_to_fetch,
            "claims": [c.model_dump(mode="json") for c in to_process],
            "session_id": session.id,
            "trace_id": session.trace_id,
            # Back-channel from RNK
            "backup_urls": rank_result.get("backup_urls", []),
            "revised_order": rank_result.get("revised_order", []),
            "fetch_priority": rank_result.get("fetch_priority", []),
        },
    )
    raw_pages = read_result.get("pages", [])
    pages_maybe = [coerce_page_content(p) for p in raw_pages]
    pages: list[PageContent] = [
        p for p in pages_maybe if p is not None and not p.error and p.markdown
    ]
    session.budget_consumed.urls_fetched += len(urls_to_fetch)
    _update_wall_seconds()

    if not pages:
        logger.warning("No pages extracted in round %s", loop_round)
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.READER,
                code=ErrorCode.UNREADABLE_PAGES,
                severity=ErrorSeverity.DEGRADED,
                retryable=True,
                root_cause=(
                    f"No readable pages extracted in round {loop_round}."
                ),
                partial_results={
                    "attempted_urls": urls_to_fetch,
                    "parser_failures": read_result.get("unreadable_urls", []),
                },
                trace_id=session.trace_id,
            ),
            session,
        )
        return None

    if session.budget_consumed.is_exhausted(budget):
        logger.info("Budget exhausted after read in round %s", loop_round)
        _emit_budget(
            session.id,
            AgentRole.READER,
            "budget_exhausted_after_read",
        )
        return None

    # ── Normalize / Deduplicate (back-channel: REA→DED) ──────────────
    normalize_result = await _run_agent(
        session,
        client,
        AgentRole.EVIDENCE_DEDUPLICATOR,
        {
            "pages": [p.model_dump(mode="json") for p in pages],
            "existing_evidence": [
                e.model_dump(mode="json") for e in accumulated_evidence
            ],
            "session_id": session.id,
            "trace_id": session.trace_id,
            # Back-channel from REA
            "extraction_fingerprints": read_result.get("fingerprints", {}),
            "chunk_ids": read_result.get("chunk_ids", []),
        },
    )
    raw_evidence = normalize_result.get("new_evidence", [])
    new_evidence_maybe = [coerce_evidence_unit(e) for e in raw_evidence]
    new_evidence: list[EvidenceUnit] = [
        e for e in new_evidence_maybe if e is not None
    ]

    novelty_tracker.new_unique_hits += len(hits)
    novelty_tracker.new_unique_pages += len(pages)
    novelty_tracker.new_supporting_evidence_spans += sum(
        len(e.quoted_passages) for e in new_evidence
    )

    seen_publishers = {
        ev.publisher_id for ev in accumulated_evidence if ev.publisher_id
    }
    new_publishers = {
        ev.publisher_id
        for ev in new_evidence
        if ev.publisher_id and ev.publisher_id not in seen_publishers
    }
    novelty_tracker.new_independent_publishers = len(new_publishers)
    session.novelty_tracker = novelty_tracker

    existing_ids = {e.id for e in accumulated_evidence}
    deduped_new = [e for e in new_evidence if e.id not in existing_ids]
    accumulated_evidence.extend(deduped_new)
    independence_graph.update(deduped_new)
    session.accumulated_evidence = accumulated_evidence
    session.independence_graph = independence_graph

    update_provenance(
        provenance_tree, to_process, hits, deduped_new, claim_queries
    )
    session.provenance_tree = provenance_tree

    _update_wall_seconds()
    if session.budget_consumed.is_exhausted(budget):
        logger.info(
            "Budget exhausted after normalize in round %s", loop_round
        )
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.EVIDENCE_DEDUPLICATOR,
                code=ErrorCode.BUDGET_EXHAUSTED_AFTER_GATHER,
                severity=ErrorSeverity.DEGRADED,
                retryable=False,
                root_cause="Budget exhausted after evidence gather.",
                trace_id=session.trace_id,
            ),
            session,
        )
        return None

    return accumulated_evidence, pages, deduped_new
