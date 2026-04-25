"""Normalize-stage helpers for evidence gathering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core import AgentRole, get_logger
from core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from workflow import (
    coerce_evidence_unit,
    emit_envelope,
    update_provenance,
)
from workflow import run_agent as _run_agent

if TYPE_CHECKING:
    from collections.abc import Callable

    from core import A2AClient
    from core.models import (
        Claim,
        EvidenceUnit,
        IndependenceGraph,
        NoveltyTracker,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )
    from tools import PageContent, WebHit

logger = get_logger(__name__)


async def run_normalize_stage(
    session: ResearchSession,
    client: A2AClient,
    budget: WorkflowBudget,
    to_process: list[Claim],
    claim_queries: list[str],
    accumulated_evidence: list[EvidenceUnit],
    independence_graph: IndependenceGraph,
    provenance_tree: ProvenanceTree,
    novelty_tracker: NoveltyTracker,
    hits: list[WebHit],
    pages: list[PageContent],
    read_result: dict[str, Any],
    update_wall_seconds: Callable[[], None],
    loop_round: int,
) -> list[EvidenceUnit] | None:
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
            "extraction_fingerprints": read_result.get("fingerprints", {}),
            "chunk_ids": read_result.get("chunk_ids", []),
        },
    )
    new_evidence = [
        evidence
        for evidence in (
            coerce_evidence_unit(raw)
            for raw in normalize_result.get("new_evidence", [])
        )
        if evidence is not None
    ]
    update_novelty_tracker(
        novelty_tracker,
        accumulated_evidence,
        hits,
        pages,
        new_evidence,
    )
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
    update_wall_seconds()
    if not session.budget_consumed.is_exhausted(budget):
        return deduped_new
    logger.info("Budget exhausted after normalize in round %s", loop_round)
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


def update_novelty_tracker(
    novelty_tracker: NoveltyTracker,
    accumulated_evidence: list[EvidenceUnit],
    hits: list[WebHit],
    pages: list[PageContent],
    new_evidence: list[EvidenceUnit],
) -> None:
    novelty_tracker.new_unique_hits += len(hits)
    novelty_tracker.new_unique_pages += len(pages)
    novelty_tracker.new_supporting_evidence_spans += sum(
        len(evidence.quoted_passages) for evidence in new_evidence
    )
    seen_publishers = {
        evidence.publisher_id
        for evidence in accumulated_evidence
        if evidence.publisher_id
    }
    novelty_tracker.new_independent_publishers = len(
        {
            evidence.publisher_id
            for evidence in new_evidence
            if evidence.publisher_id
            and evidence.publisher_id not in seen_publishers
        }
    )
