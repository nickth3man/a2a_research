"""Provenance tree helpers for the workflow engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.backend.core.models import (
    ProvenanceEdgeType,
    ProvenanceNode,
    ProvenanceTree,
)
from a2a_research.backend.workflow.provenance import (
    claim_node_id,
    ensure_edge,
    ensure_node,
    hit_node_id,
    page_node_id,
    passage_node_id,
    query_node_id,
)

if TYPE_CHECKING:
    from a2a_research.backend.core.models import Claim, EvidenceUnit
    from a2a_research.backend.tools import WebHit

__all__ = ["update_provenance"]


def update_provenance(
    provenance_tree: ProvenanceTree,
    to_process: list[Claim],
    hits: list[WebHit],
    deduped_new: list[EvidenceUnit],
    claim_queries: list[str],
) -> None:
    """Update provenance tree with new evidence."""
    for claim in to_process:
        claim_node = claim_node_id(claim.id)
        ensure_node(
            provenance_tree,
            ProvenanceNode(id=claim_node, node_type="claim", ref_id=claim.id),
        )
    for hit in hits:
        hit_node = hit_node_id(hit.url)
        ensure_node(
            provenance_tree,
            ProvenanceNode(
                id=hit_node,
                node_type="hit",
                ref_id=hit.url,
                metadata={
                    "title": hit.title,
                    "source": hit.source,
                    "score": hit.score,
                },
            ),
        )
    for claim in to_process:
        claim_node = claim_node_id(claim.id)
        for query_text in claim_queries:
            query_node = query_node_id(claim.id, query_text)
            ensure_node(
                provenance_tree,
                ProvenanceNode(
                    id=query_node,
                    node_type="query",
                    ref_id=query_text,
                    metadata={"claim_id": claim.id},
                ),
            )
            ensure_edge(
                provenance_tree,
                claim_node,
                query_node,
                ProvenanceEdgeType.CLAIM_TO_QUERY,
            )
            for hit in hits:
                ensure_edge(
                    provenance_tree,
                    query_node,
                    hit_node_id(hit.url),
                    ProvenanceEdgeType.QUERY_TO_HIT,
                )
    for ev in deduped_new:
        page_node = page_node_id(ev.id)
        ensure_node(
            provenance_tree,
            ProvenanceNode(
                id=page_node,
                node_type="page",
                ref_id=ev.id,
                metadata={"url": ev.url, "title": ev.title},
            ),
        )
        ensure_edge(
            provenance_tree,
            hit_node_id(ev.url),
            page_node,
            ProvenanceEdgeType.HIT_TO_PAGE,
        )
        for passage in ev.quoted_passages:
            passage_node = passage_node_id(passage.id)
            ensure_node(
                provenance_tree,
                ProvenanceNode(
                    id=passage_node,
                    node_type="passage",
                    ref_id=passage.id,
                    metadata={"evidence_id": ev.id},
                ),
            )
            ensure_edge(
                provenance_tree,
                page_node,
                passage_node,
                ProvenanceEdgeType.PAGE_TO_PASSAGE,
            )
