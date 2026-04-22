"""FactChecker agent output model.

Structured output contract for the LangGraph-based FactChecker agent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from a2a_research.models.enums import Verdict
from a2a_research.models.verification import ClaimState
from a2a_research.models.workflow import BudgetConsumption

if TYPE_CHECKING:
    from a2a_research.models.claims import ClaimFollowUp, ReplanReason


class FactCheckerOutput(BaseModel):
    """Output contract for the FactChecker agent."""

    updated_claim_state: ClaimState = Field(default_factory=ClaimState)
    claim_follow_ups: list[ClaimFollowUp] = Field(default_factory=list)
    budget_consumed: BudgetConsumption = Field(
        default_factory=BudgetConsumption
    )
    replan_reasons: list[ReplanReason] = Field(default_factory=list)
    stale_dependents: list[str] = Field(default_factory=list)
    cached_verifications: list[str] = Field(default_factory=list)

    @property
    def needs_replan(self) -> bool:
        """True if any replan reasons were emitted."""
        return bool(self.replan_reasons)

    @property
    def tentatively_supported_claim_ids(self) -> list[str]:
        """Claim IDs that are SUPPORTED but not yet adversary-checked."""
        return [
            cid
            for cid, v in self.updated_claim_state.verification.items()
            if v.verdict == Verdict.SUPPORTED
            and v.adversary_result == "NOT_RUN"
        ]
