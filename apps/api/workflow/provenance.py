"""Provenance tree helpers for tracking evidence lineage."""

from __future__ import annotations

import hashlib

from core.models import (
    ProvenanceEdge,
    ProvenanceEdgeType,
    ProvenanceNode,
    ProvenanceTree,
)

__all__ = [
    "challenge_node_id",
    "claim_node_id",
    "ensure_edge",
    "ensure_node",
    "hit_node_id",
    "page_node_id",
    "passage_node_id",
    "query_node_id",
    "verdict_node_id",
]


def ensure_node(tree: ProvenanceTree, node: ProvenanceNode) -> None:
    if node.id not in tree.nodes:
        tree.add_node(node)


def ensure_edge(
    tree: ProvenanceTree,
    src: str,
    dst: str,
    edge_type: ProvenanceEdgeType,
) -> None:
    exists = any(
        edge.src == src and edge.dst == dst and edge.edge_type == edge_type
        for edge in tree.edges
    )
    if not exists:
        tree.add_edge(ProvenanceEdge(src=src, dst=dst, edge_type=edge_type))


def claim_node_id(claim_id: str) -> str:
    return f"claim::{claim_id}"


def query_node_id(claim_id: str, query_text: str) -> str:
    digest = hashlib.sha1(
        query_text.encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:12]
    return f"query::{claim_id}::{digest}"


def hit_node_id(url: str) -> str:
    return f"hit::{url}"


def page_node_id(evidence_id: str) -> str:
    return f"page::{evidence_id}"


def passage_node_id(passage_id: str) -> str:
    return f"passage::{passage_id}"


def verdict_node_id(claim_id: str) -> str:
    return f"verdict::{claim_id}"


def challenge_node_id(claim_id: str) -> str:
    return f"challenge::{claim_id}"
