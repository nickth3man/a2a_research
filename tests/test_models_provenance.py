"""Tests for ProvenanceTree, ProvenanceNode, ProvenanceEdge."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from a2a_research.models import (
    ProvenanceEdge,
    ProvenanceEdgeType,
    ProvenanceNode,
    ProvenanceTree,
)


class TestProvenanceNode:
    def test_defaults(self):
        n = ProvenanceNode()
        assert n.id.startswith("prv_")
        assert n.node_type == "claim"
        assert n.ref_id == ""
        assert n.metadata == {}

    def test_all_node_types(self):
        for nt in (
            "claim",
            "query",
            "hit",
            "page",
            "passage",
            "verdict",
            "challenge",
        ):
            n = ProvenanceNode(node_type=nt)
            assert n.node_type == nt

    def test_invalid_node_type(self):
        with pytest.raises(ValidationError):
            ProvenanceNode(node_type="invalid")

    def test_custom_metadata(self):
        n = ProvenanceNode(metadata={"key": "value", "num": 42})
        assert n.metadata["key"] == "value"

    def test_serialization_roundtrip(self):
        n = ProvenanceNode(
            node_type="passage", ref_id="psg_123", metadata={"score": 0.9}
        )
        data = n.model_dump()
        restored = ProvenanceNode.model_validate(data)
        assert restored.node_type == n.node_type
        assert restored.ref_id == n.ref_id


class TestProvenanceEdge:
    def test_defaults(self):
        e = ProvenanceEdge(src="n1", dst="n2")
        assert e.edge_type == ProvenanceEdgeType.CLAIM_TO_QUERY
        assert e.weight == 1.0

    def test_all_edge_types(self):
        for et in ProvenanceEdgeType:
            e = ProvenanceEdge(src="n1", dst="n2", edge_type=et)
            assert e.edge_type == et

    def test_custom_weight(self):
        e = ProvenanceEdge(src="n1", dst="n2", weight=0.5)
        assert e.weight == 0.5


class TestProvenanceTree:
    def test_empty_tree(self):
        tree = ProvenanceTree()
        assert tree.nodes == {}
        assert tree.edges == []

    def test_add_node(self):
        tree = ProvenanceTree()
        node = ProvenanceNode(id="n1", node_type="claim", ref_id="clm_1")
        tree.add_node(node)
        assert "n1" in tree.nodes
        assert tree.nodes["n1"].ref_id == "clm_1"

    def test_add_node_overwrites(self):
        tree = ProvenanceTree()
        tree.add_node(ProvenanceNode(id="n1", ref_id="first"))
        tree.add_node(ProvenanceNode(id="n1", ref_id="second"))
        assert tree.nodes["n1"].ref_id == "second"

    def test_add_edge(self):
        tree = ProvenanceTree()
        edge = ProvenanceEdge(
            src="n1", dst="n2", edge_type=ProvenanceEdgeType.CLAIM_TO_QUERY
        )
        tree.add_edge(edge)
        assert len(tree.edges) == 1
        assert tree.edges[0].src == "n1"

    def test_path_for_citation_found(self):
        tree = ProvenanceTree()
        node = ProvenanceNode(id="psg_1", node_type="passage")
        tree.add_node(node)
        result = tree.path_for_citation("psg_1")
        assert len(result) == 1
        assert result[0].id == "psg_1"

    def test_path_for_citation_not_found(self):
        tree = ProvenanceTree()
        result = tree.path_for_citation("nonexistent")
        assert result == []

    def test_sources_for_claim(self):
        tree = ProvenanceTree()
        tree.add_node(ProvenanceNode(id="n1", ref_id="clm_1"))
        tree.add_node(ProvenanceNode(id="n2", ref_id="clm_1"))
        tree.add_node(ProvenanceNode(id="n3", ref_id="clm_2"))
        sources = tree.sources_for_claim("clm_1")
        assert len(sources) == 2
        assert all(s.ref_id == "clm_1" for s in sources)

    def test_sources_for_claim_empty(self):
        tree = ProvenanceTree()
        assert tree.sources_for_claim("nonexistent") == []

    def test_full_lineage(self):
        tree = ProvenanceTree()
        tree.add_node(
            ProvenanceNode(id="claim_1", node_type="claim", ref_id="clm_1")
        )
        tree.add_node(
            ProvenanceNode(id="query_1", node_type="query", ref_id="q1")
        )
        tree.add_node(ProvenanceNode(id="hit_1", node_type="hit", ref_id="h1"))
        tree.add_edge(
            ProvenanceEdge(
                src="claim_1",
                dst="query_1",
                edge_type=ProvenanceEdgeType.CLAIM_TO_QUERY,
            )
        )
        tree.add_edge(
            ProvenanceEdge(
                src="query_1",
                dst="hit_1",
                edge_type=ProvenanceEdgeType.QUERY_TO_HIT,
            )
        )
        assert len(tree.nodes) == 3
        assert len(tree.edges) == 2
