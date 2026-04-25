"""Tests for core.models.fact_checker — FactCheckerOutput."""

from __future__ import annotations

from core.models.claims import ClaimFollowUp, ReplanReason
from core.models.enums import ReplanReasonCode, Verdict
from core.models.fact_checker import FactCheckerOutput
from core.models.verification import ClaimState, ClaimVerification

# Resolve forward references declared under TYPE_CHECKING guard in
# fact_checker.py — necessary on isolated test workers (xdist) where
# the full core.models init chain hasn't been executed on this worker.
FactCheckerOutput.model_rebuild()


class TestFactCheckerOutput:
    def test_needs_replan_false_when_empty(self) -> None:
        output = FactCheckerOutput()
        assert output.needs_replan is False
        assert ClaimFollowUp is not None

    def test_needs_replan_true_when_reasons_present(self) -> None:
        reason = ReplanReason(
            claim_id="clm_1", code=ReplanReasonCode.TOO_BROAD
        )
        output = FactCheckerOutput(replan_reasons=[reason])
        assert output.needs_replan is True

    def test_tentatively_supported_empty_when_no_claims(self) -> None:
        output = FactCheckerOutput()
        assert output.tentatively_supported_claim_ids == []

    def test_tentatively_supported_returns_supported_not_adversary_checked(
        self,
    ) -> None:
        state = ClaimState(
            verification={
                "clm_a": ClaimVerification(
                    claim_id="clm_a",
                    verdict=Verdict.SUPPORTED,
                    adversary_result="NOT_RUN",
                ),
                "clm_b": ClaimVerification(
                    claim_id="clm_b",
                    verdict=Verdict.REFUTED,
                    adversary_result="NOT_RUN",
                ),
                "clm_c": ClaimVerification(
                    claim_id="clm_c",
                    verdict=Verdict.SUPPORTED,
                    adversary_result="HOLDS",
                ),
            }
        )
        output = FactCheckerOutput(updated_claim_state=state)
        result = output.tentatively_supported_claim_ids
        assert "clm_a" in result
        assert "clm_b" not in result
        assert "clm_c" not in result
