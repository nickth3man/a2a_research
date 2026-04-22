"""Tests for ClaimVerification."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from a2a_research.models import ClaimVerification, Verdict


class TestClaimVerification:
    def test_defaults(self):
        cv = ClaimVerification(claim_id="clm_1")
        assert cv.verdict == Verdict.UNRESOLVED
        assert cv.confidence == 0.0
        assert cv.independent_source_count == 0
        assert cv.supporting_evidence_ids == []
        assert cv.refuting_evidence_ids == []
        assert cv.contradictions == []
        assert cv.adversary_result == "NOT_RUN"
        assert cv.revision_history == []

    def test_custom_values(self):
        cv = ClaimVerification(
            claim_id="clm_1",
            verdict=Verdict.SUPPORTED,
            confidence=0.85,
            independent_source_count=3,
            supporting_evidence_ids=["ev1", "ev2"],
            adversary_result="HOLDS",
        )
        assert cv.verdict == Verdict.SUPPORTED
        assert cv.confidence == 0.85
        assert cv.adversary_result == "HOLDS"

    def test_all_adversary_results(self):
        for result in ("HOLDS", "WEAKENED", "REFUTED", "NOT_RUN"):
            cv = ClaimVerification(claim_id="c", adversary_result=result)
            assert cv.adversary_result == result

    def test_invalid_adversary_result(self):
        with pytest.raises(ValidationError):
            ClaimVerification(claim_id="c", adversary_result="INVALID")
