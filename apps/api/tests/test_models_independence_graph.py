"""Tests for IndependenceGraph model."""

from __future__ import annotations

from core.models import (
    EvidenceUnit,
    IndependenceGraph,
    Passage,
)


class TestIndependenceGraph:
    def test_empty(self):
        ig = IndependenceGraph()
        assert ig.independent_source_count("c1") == 0

    def test_single_publisher(self):
        ig = IndependenceGraph(claim_to_publishers={"c1": {"pub1"}})
        assert ig.independent_source_count("c1") == 1

    def test_multiple_independent_publishers(self):
        ig = IndependenceGraph(
            claim_to_publishers={"c1": {"pub1", "pub2", "pub3"}}
        )
        assert ig.independent_source_count("c1") == 3

    def test_unknown_claim_returns_zero(self):
        ig = IndependenceGraph(claim_to_publishers={"c1": {"pub1"}})
        assert ig.independent_source_count("c99") == 0

    def test_update_from_evidence(self):
        p1 = Passage(
            evidence_id="ev1", text="t", claim_relevance_scores={"c1": 0.9}
        )
        eu = EvidenceUnit(
            url="https://x.com", publisher_id="pub1", quoted_passages=[p1]
        )
        ig = IndependenceGraph()
        ig.update([eu])
        assert ig.independent_source_count("c1") == 1

    def test_update_multiple_evidence_same_publisher(self):
        p1 = Passage(
            evidence_id="ev1", text="t", claim_relevance_scores={"c1": 0.9}
        )
        p2 = Passage(
            evidence_id="ev2", text="t", claim_relevance_scores={"c1": 0.8}
        )
        eu1 = EvidenceUnit(
            url="https://a.com", publisher_id="pub1", quoted_passages=[p1]
        )
        eu2 = EvidenceUnit(
            url="https://b.com", publisher_id="pub1", quoted_passages=[p2]
        )
        ig = IndependenceGraph()
        ig.update([eu1, eu2])
        assert ig.independent_source_count("c1") == 1

    def test_update_different_publishers(self):
        p1 = Passage(
            evidence_id="ev1", text="t", claim_relevance_scores={"c1": 0.9}
        )
        p2 = Passage(
            evidence_id="ev2", text="t", claim_relevance_scores={"c1": 0.8}
        )
        eu1 = EvidenceUnit(
            url="https://a.com", publisher_id="pub1", quoted_passages=[p1]
        )
        eu2 = EvidenceUnit(
            url="https://b.com", publisher_id="pub2", quoted_passages=[p2]
        )
        ig = IndependenceGraph()
        ig.update([eu1, eu2])
        assert ig.independent_source_count("c1") == 2

    def test_update_empty_publisher_ignored(self):
        p = Passage(
            evidence_id="ev1", text="t", claim_relevance_scores={"c1": 0.9}
        )
        eu = EvidenceUnit(
            url="https://x.com", publisher_id="", quoted_passages=[p]
        )
        ig = IndependenceGraph()
        ig.update([eu])
        assert ig.independent_source_count("c1") == 0

    def test_update_multiple_claims(self):
        p1 = Passage(
            evidence_id="ev1",
            text="t",
            claim_relevance_scores={"c1": 0.9, "c2": 0.5},
        )
        eu = EvidenceUnit(
            url="https://x.com", publisher_id="pub1", quoted_passages=[p1]
        )
        ig = IndependenceGraph()
        ig.update([eu])
        assert ig.independent_source_count("c1") == 1
        assert ig.independent_source_count("c2") == 1

    def test_syndication_clusters_stored(self):
        ig = IndependenceGraph(
            syndication_clusters={"cluster_a": ["pub1", "pub2"]}
        )
        assert ig.syndication_clusters["cluster_a"] == ["pub1", "pub2"]

    def test_citation_chains_stored(self):
        ig = IndependenceGraph(citation_chains={"chain_1": ["a", "b", "c"]})
        assert ig.citation_chains["chain_1"] == ["a", "b", "c"]

    def test_update_adds_evidence_to_syndication_clusters(self):
        """update() populates syndication_clusters"""
        ig = IndependenceGraph()
        eu = EvidenceUnit(
            url="https://x.com",
            publisher_id="pub1",
            syndication_cluster_id="cluster_a",
        )
        ig.update([eu])
        assert "cluster_a" in ig.syndication_clusters
        assert eu.id in ig.syndication_clusters["cluster_a"]

    def test_update_avoids_duplicate_in_syndication_cluster(self):
        """update() does not add duplicates in syndication clusters"""
        ig = IndependenceGraph(
            syndication_clusters={"cluster_a": ["existing_id"]}
        )
        eu = EvidenceUnit(
            id="existing_id",
            url="https://x.com",
            publisher_id="pub1",
            syndication_cluster_id="cluster_a",
        )
        ig.update([eu])
        assert ig.syndication_clusters["cluster_a"] == ["existing_id"]
