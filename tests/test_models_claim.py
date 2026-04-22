"""Tests for Claim, FreshnessWindow core domain models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from a2a_research.backend.core.models import Claim, FreshnessWindow, Verdict


class TestFreshnessWindow:
    def test_defaults(self):
        fw = FreshnessWindow()
        assert fw.max_age_days is None
        assert fw.strict is False
        assert fw.rationale == ""

    def test_custom_values(self):
        fw = FreshnessWindow(
            max_age_days=7, strict=True, rationale="news claim"
        )
        assert fw.max_age_days == 7
        assert fw.strict is True
        assert fw.rationale == "news claim"

    def test_serialization_roundtrip(self):
        fw = FreshnessWindow(max_age_days=3, strict=True, rationale="test")
        data = fw.model_dump()
        restored = FreshnessWindow.model_validate(data)
        assert restored == fw


class TestClaim:
    def test_auto_generated_id(self):
        c = Claim(text="The sky is blue")
        assert c.id.startswith("clm_")
        assert len(c.id) == 12

    def test_custom_id(self):
        c = Claim(id="clm_custom", text="test")
        assert c.id == "clm_custom"

    def test_empty_id_rejected(self):
        with pytest.raises(ValidationError, match="non-empty string"):
            Claim(id="", text="test")

    def test_none_id_rejected(self):
        with pytest.raises(ValidationError, match="non-empty string"):
            Claim(id=None, text="test")

    def test_whitespace_only_id_rejected(self):
        with pytest.raises(ValidationError, match="non-empty string"):
            Claim(id="   ", text="test")

    def test_integer_id_coerced(self):
        c = Claim(id=42, text="test")
        assert c.id == "42"

    def test_default_freshness(self):
        c = Claim(text="test")
        assert isinstance(c.freshness, FreshnessWindow)
        assert c.freshness.max_age_days is None

    def test_default_verdict(self):
        c = Claim(text="test")
        assert c.verdict == Verdict.UNRESOLVED

    def test_default_confidence(self):
        c = Claim(text="test")
        assert c.confidence == 0.5

    def test_confidence_bounds_low(self):
        with pytest.raises(ValidationError):
            Claim(text="test", confidence=-0.1)

    def test_confidence_bounds_high(self):
        with pytest.raises(ValidationError):
            Claim(text="test", confidence=1.1)

    def test_confidence_boundary_zero(self):
        c = Claim(text="test", confidence=0.0)
        assert c.confidence == 0.0

    def test_confidence_boundary_one(self):
        c = Claim(text="test", confidence=1.0)
        assert c.confidence == 1.0

    def test_default_lists_empty(self):
        c = Claim(text="test")
        assert c.sources == []
        assert c.evidence_snippets == []

    def test_created_at_auto_set(self):
        before = datetime.now(UTC)
        c = Claim(text="test")
        after = datetime.now(UTC)
        assert before <= c.created_at <= after

    def test_serialization_roundtrip(self):
        c = Claim(
            text="Water boils at 100C",
            confidence=0.9,
            verdict=Verdict.SUPPORTED,
            sources=["url1"],
        )
        data = c.model_dump()
        restored = Claim.model_validate(data)
        assert restored.text == c.text
        assert restored.confidence == c.confidence
        assert restored.verdict == c.verdict
        assert restored.sources == c.sources

    def test_text_required(self):
        with pytest.raises(ValidationError):
            Claim()
