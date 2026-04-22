"""Provenance tracking models.

Models for tracking the lineage of claims, queries, hits, pages, passages,
and verdicts through a directed graph.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from a2a_research.backend.core.models.enums import ProvenanceEdgeType


class ProvenanceNode(BaseModel):
    """Node in the provenance tree."""

    id: str = Field(default_factory=lambda: f"prv_{uuid.uuid4().hex[:8]}")
    node_type: Literal[
        "claim", "query", "hit", "page", "passage", "verdict", "challenge"
    ] = "claim"
    ref_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceEdge(BaseModel):
    """Edge in the provenance tree."""

    src: str
    dst: str
    edge_type: ProvenanceEdgeType = ProvenanceEdgeType.CLAIM_TO_QUERY
    weight: float = 1.0


class ProvenanceTree(BaseModel):
    """Tracks the lineage of every claim, query, hit, page, passage,
    and verdict.
    """

    nodes: dict[str, ProvenanceNode] = Field(default_factory=dict)
    edges: list[ProvenanceEdge] = Field(default_factory=list)

    def add_node(self, node: ProvenanceNode) -> None:
        """Add a node to the tree."""
        self.nodes[node.id] = node

    def add_edge(self, edge: ProvenanceEdge) -> None:
        """Add an edge to the tree."""
        self.edges.append(edge)

    def path_for_citation(self, passage_id: str) -> list[ProvenanceNode]:
        """Return the provenance path for a passage citation."""
        result: list[ProvenanceNode] = []
        current = self.nodes.get(passage_id)
        if current is None:
            for node in self.nodes.values():
                if node.ref_id == passage_id:
                    current = node
                    break
        if current is None:
            return result
        reverse_edges: dict[str, list[str]] = {}
        for edge in self.edges:
            reverse_edges.setdefault(edge.dst, []).append(edge.src)
        cursor: ProvenanceNode | None = current
        visited: set[str] = set()
        chain: list[ProvenanceNode] = []
        while cursor is not None and cursor.id not in visited:
            visited.add(cursor.id)
            chain.append(cursor)
            parents = reverse_edges.get(cursor.id, [])
            cursor = self.nodes.get(parents[0]) if parents else None
        chain.reverse()
        return chain

    def sources_for_claim(self, claim_id: str) -> list[ProvenanceNode]:
        """Return source nodes for a claim."""
        direct_matches = [
            n for n in self.nodes.values() if n.ref_id == claim_id
        ]
        claim_node_ids = {
            node.id
            for node in self.nodes.values()
            if node.node_type == "claim" and node.ref_id == claim_id
        }
        if not claim_node_ids:
            return direct_matches
        reachable: set[str] = set(claim_node_ids)
        queue = list(claim_node_ids)
        while queue:
            current = queue.pop(0)
            for edge in self.edges:
                if edge.src == current and edge.dst not in reachable:
                    reachable.add(edge.dst)
                    queue.append(edge.dst)
        derived_sources = [
            self.nodes[node_id]
            for node_id in reachable
            if node_id in self.nodes
            and self.nodes[node_id].node_type in {"hit", "page", "passage"}
        ]
        return derived_sources or direct_matches
