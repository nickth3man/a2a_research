"""Tests for EvidenceUnit model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.models import (
    CredibilitySignals,
    EvidenceUnit,
    Passage,
)


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
