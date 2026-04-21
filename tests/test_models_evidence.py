"""Tests for EvidenceUnit, IndependenceGraph, Passage, CredibilitySignals."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from a2a_research.models import (
    CredibilitySignals,
    EvidenceUnit,
    IndependenceGraph,
    Passage,
)


class TestPassage:
    def test_defaults(self):
        p = Passage(evidence_id="ev1", text="some text")
        assert p.id.startswith("psg_")
        assert p.evidence_id == "ev1"
        assert p.text == "some text"
        assert p.claim_relevance_scores == {}
        assert p.is_quotation is False

    def test_with_relevance_scores(self):
        p = Passage(
            evidence_id="ev1",
            text="text",
            claim_relevance_scores={"clm_1": 0.9, "clm_2": 0.3},
        )
        assert p.claim_relevance_scores["clm_1"] == 0.9

    def test_serialization_roundtrip(self):
        p = Passage(evidence_id="ev1", text="text", is_quotation=True)
        data = p.model_dump()
        restored = Passage.model_validate(data)
        assert restored == p


class TestCredibilitySignals:
    def test_defaults(self):
        cs = CredibilitySignals()
        assert cs.domain_reputation == 0.0
        assert cs.author_verified is False
        assert cs.has_citations is False
        assert cs.content_freshness_days is None

    def test_custom(self):
        cs = CredibilitySignals(
            domain_reputation=0.8,
            author_verified=True,
            has_citations=True,
            content_freshness_days=2,
        )
        assert cs.domain_reputation == 0.8
        assert cs.content_freshness_days == 2


class TestEvidenceUnit:
    def test_defaults(self):
        eu = EvidenceUnit(url="https://example.com")
        assert eu.id.startswith("evu_")
        assert eu.url == "https://example.com"
        assert eu.source_type == "other"
        assert eu.quoted_passages == []
        assert isinstance(eu.credibility_signals, CredibilitySignals)
        assert eu.fetched_at.tzinfo is not None

    def test_all_source_types(self):
        for st in (
            "academic",
            "news",
            "blog",
            "wiki",
            "forum",
            "social",
            "other",
        ):
            eu = EvidenceUnit(url="https://x.com", source_type=st)
            assert eu.source_type == st

    def test_invalid_source_type(self):
        with pytest.raises(ValidationError):
            EvidenceUnit(url="https://x.com", source_type="government")

    def test_with_passages(self):
        p = Passage(
            evidence_id="ev1",
            text="relevant snippet",
            claim_relevance_scores={"c1": 0.8},
        )
        eu = EvidenceUnit(url="https://example.com", quoted_passages=[p])
        assert len(eu.quoted_passages) == 1
        assert eu.quoted_passages[0].text == "relevant snippet"

    def test_syndication_cluster(self):
        eu = EvidenceUnit(
            url="https://example.com", syndication_cluster_id="cluster_1"
        )
        assert eu.syndication_cluster_id == "cluster_1"

    def test_no_syndication(self):
        eu = EvidenceUnit(url="https://example.com")
        assert eu.syndication_cluster_id is None

    def test_serialization_roundtrip(self):
        eu = EvidenceUnit(
            url="https://example.com",
            title="Test",
            domain_authority=0.7,
            publisher_id="pub1",
        )
        data = eu.model_dump()
        restored = EvidenceUnit.model_validate(data)
        assert restored.url == eu.url
        assert restored.title == eu.title
        assert restored.domain_authority == eu.domain_authority


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
