"""Workflow evidence, adversary, and verification configuration mixin."""

from __future__ import annotations

from pydantic import Field


class EvidenceAdversaryVerificationMixin:
    """Mixin providing evidence, adversary, and verification fields."""

    # -- Evidence
    evidence_deduplication: bool = Field(
        default=True,
        description="Deduplicate chunks (env: WF_EVIDENCE__DEDUPLICATION).",
    )
    evidence_chunk_size: int = Field(
        default=1000,
        ge=100,
        description="Chunk size chars (env: WF_EVIDENCE__CHUNK_SIZE).",
    )
    evidence_chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Chunk overlap (env: WF_EVIDENCE__CHUNK_OVERLAP).",
    )
    evidence_source_independence: bool = Field(
        default=True,
        description="Track independent sources "
        "(env: WF_EVIDENCE__SOURCE_INDEPENDENCE).",
    )

    # -- Adversary
    adversary_enabled: bool = Field(
        default=True,
        description="Enable adversary (env: WF_ADVERSARY__ENABLED).",
    )
    adversary_trigger: str = Field(
        default="on_tentative_supported",
        description="Adversary trigger (env: WF_ADVERSARY__TRIGGER).",
    )
    adversary_inversion_query_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Counter-query count "
        "(env: WF_ADVERSARY__INVERSION_QUERY_COUNT).",
    )
    adversary_counter_expert_lookup: bool = Field(
        default=True,
        description="Counter-expert lookup "
        "(env: WF_ADVERSARY__COUNTER_EXPERT_LOOKUP).",
    )

    # -- Verification
    verification_cache_results: bool = Field(
        default=True,
        description="Cache results (env: WF_VERIFICATION__CACHE_RESULTS).",
    )
    verification_confidence_auto_accept_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Auto-accept confidence "
        "(env: WF_VERIFICATION__"
        "CONFIDENCE_AUTO_ACCEPT_THRESHOLD).",
    )
    verification_short_circuit_when_adversary_holds: bool = Field(
        default=True,
        description="Short-circuit if adversary holds "
        "(env: WF_VERIFICATION__"
        "SHORT_CIRCUIT_WHEN_ADVERSARY_HOLDS).",
    )
