"""Tests for Passage and CredibilitySignals models."""

from __future__ import annotations

from a2a_research.models import (
    CredibilitySignals,
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
