"""Claim verification state models.

Models for tracking verification results and aggregated claim state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from a2a_research.models.claims import Claim, ClaimDAG, FreshnessWindow
from a2a_research.models.enums import Verdict


def _default_claim_dag() -> ClaimDAG:
    """Factory to avoid circular import at module load time."""
    return ClaimDAG()


class VerificationRevision(BaseModel):
    """Record of a change in verification verdict."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    previous_verdict: Literal[
        "SUPPORTED", "REFUTED", "MIXED", "UNRESOLVED", "STALE"
    ]
    new_verdict: Literal[
        "SUPPORTED", "REFUTED", "MIXED", "UNRESOLVED", "STALE"
    ]
    reason: str
    evidence_delta: list[str] = Field(default_factory=list)


class ClaimVerification(BaseModel):
    """Mutable verification state for a claim."""

    claim_id: str
    verdict: Verdict = Verdict.UNRESOLVED
    confidence: float = 0.0
    independent_source_count: int = 0
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    refuting_evidence_ids: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    adversary_result: Literal["HOLDS", "WEAKENED", "REFUTED", "NOT_RUN"] = (
        "NOT_RUN"
    )
    revision_history: list[VerificationRevision] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClaimState(BaseModel):
    """Aggregated verification state for all claims."""

    original_claims: list[Claim] = Field(default_factory=list)
    dag: ClaimDAG = Field(default_factory=lambda: _default_claim_dag())
    verification: dict[str, ClaimVerification] = Field(default_factory=dict)
    unresolved_claim_ids: list[str] = Field(default_factory=list)
    stale_claim_ids: list[str] = Field(default_factory=list)
    resolved_claim_ids: list[str] = Field(default_factory=list)

    def mark_dependents_stale(self, parent_id: str) -> None:
        """Cascade STALE to descendants when a parent verdict flips."""
        # Import here to avoid circular dependency at module load time.

        for descendant in self.dag.descendants_of(parent_id):
            v = self.verification.get(descendant)
            if v is not None:
                v.verdict = Verdict.STALE
                if descendant in self.unresolved_claim_ids:
                    self.unresolved_claim_ids.remove(descendant)
                if descendant not in self.stale_claim_ids:
                    self.stale_claim_ids.append(descendant)
                if descendant in self.resolved_claim_ids:
                    self.resolved_claim_ids.remove(descendant)

    def refresh_resolution_lists(self) -> None:
        """Derive lists from current verification verdicts."""
        unresolved: list[str] = []
        stale: list[str] = []
        resolved: list[str] = []
        ordered_claim_ids = [claim.id for claim in self.original_claims]
        for claim_id in self.verification:
            if claim_id not in ordered_claim_ids:
                ordered_claim_ids.append(claim_id)
        for claim_id in ordered_claim_ids:
            verification = self.verification.get(claim_id)
            verdict = (
                verification.verdict
                if verification is not None
                else Verdict.UNRESOLVED
            )
            if verdict == Verdict.STALE:
                stale.append(claim_id)
            elif verdict == Verdict.UNRESOLVED:
                unresolved.append(claim_id)
            else:
                resolved.append(claim_id)
        self.unresolved_claim_ids = unresolved
        self.stale_claim_ids = stale
        self.resolved_claim_ids = resolved

    def get_claim(self, claim_id: str) -> Claim | None:
        """Get a claim by ID from original_claims."""
        for claim in self.original_claims:
            if claim.id == claim_id:
                return claim
        return None

    @property
    def all_resolved(self) -> bool:
        """True if no unresolved or stale claims remain."""
        return not self.unresolved_claim_ids and not self.stale_claim_ids

    @property
    def tentatively_supported_claim_ids(self) -> list[str]:
        """Claim IDs that are SUPPORTED but not yet adversary-checked."""
        return [
            cid
            for cid, v in self.verification.items()
            if v.verdict == Verdict.SUPPORTED
            and v.adversary_result == "NOT_RUN"
        ]

    @property
    def unresolved_or_stale_claims(self) -> list[Claim]:
        """Get Claim objects that are unresolved or stale."""
        ids = set(self.unresolved_claim_ids + self.stale_claim_ids)
        return [c for c in self.original_claims if c.id in ids]

    @property
    def unresolved_or_stale_claim_ids(self) -> list[str]:
        """Get IDs of unresolved or stale claims."""
        return list(set(self.unresolved_claim_ids + self.stale_claim_ids))

    @property
    def freshness_windows(self) -> dict[str, FreshnessWindow]:
        """Map claim IDs to their freshness windows."""
        return {c.id: c.freshness for c in self.original_claims}
