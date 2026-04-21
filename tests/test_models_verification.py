"""Tests for VerificationRevision."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from a2a_research.models import VerificationRevision


class TestVerificationRevision:
    def test_creation(self):
        rev = VerificationRevision(
            previous_verdict="UNRESOLVED",
            new_verdict="SUPPORTED",
            reason="Found 3 independent sources",
            evidence_delta=["ev1", "ev2", "ev3"],
        )
        assert rev.previous_verdict == "UNRESOLVED"
        assert rev.new_verdict == "SUPPORTED"
        assert rev.reason == "Found 3 independent sources"
        assert len(rev.evidence_delta) == 3
        assert rev.timestamp is not None

    def test_default_evidence_delta_empty(self):
        rev = VerificationRevision(
            previous_verdict="SUPPORTED",
            new_verdict="STALE",
            reason="Parent claim refuted",
        )
        assert rev.evidence_delta == []

    def test_invalid_verdict(self):
        with pytest.raises(ValidationError):
            VerificationRevision(
                previous_verdict="INVALID",
                new_verdict="SUPPORTED",
                reason="test",
            )

    def test_all_verdict_pairs(self):
        valid = ["SUPPORTED", "REFUTED", "MIXED", "UNRESOLVED", "STALE"]
        for prev in valid:
            for new in valid:
                rev = VerificationRevision(
                    previous_verdict=prev, new_verdict=new, reason="test"
                )
                assert rev.previous_verdict == prev
                assert rev.new_verdict == new

    def test_serialization_roundtrip(self):
        rev = VerificationRevision(
            previous_verdict="MIXED",
            new_verdict="SUPPORTED",
            reason="New evidence",
            evidence_delta=["ev_new"],
        )
        data = rev.model_dump()
        restored = VerificationRevision.model_validate(data)
        assert restored.previous_verdict == rev.previous_verdict
        assert restored.new_verdict == rev.new_verdict
        assert restored.evidence_delta == rev.evidence_delta
