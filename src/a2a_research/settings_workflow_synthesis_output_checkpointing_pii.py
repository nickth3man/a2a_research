"""Workflow synthesis, output, checkpointing, and PII configuration mixin."""

from __future__ import annotations

from pydantic import Field


class SynthesisOutputCheckpointingPIIMixin:
    """Mixin providing synthesis, output, checkpointing, and PII fields."""

    # -- Synthesis
    synthesis_streaming: str = Field(
        default="sse_via_coordinator",
        description="Streaming mode (env: WF_SYNTHESIS__STREAMING).",
    )
    synthesis_tentative_snapshot_strategy: str = Field(
        default="cheap_template_every_round_plus_full_on_exit",
        description="Snapshot strategy "
        "(env: WF_SYNTHESIS__"
        "TENTATIVE_SNAPSHOT_STRATEGY).",
    )

    # -- Output
    output_formats: list[str] = Field(
        default=["markdown", "json"],
        description="Allowed output formats (env: WF_OUTPUT__FORMATS).",
    )
    output_citation_style: str = Field(
        default="hyperlinked_footnotes",
        description="Citation style (env: WF_OUTPUT__CITATION_STYLE).",
    )

    # -- Checkpointing
    checkpointing_enabled: bool = Field(
        default=True,
        description="Enable checkpointing "
        "(env: WF_CHECKPOINTING__ENABLED).",
    )
    checkpointing_stages: list[str] = Field(
        default=["plan", "verify", "adversary_gate", "synthesize"],
        description="Checkpoint stages (env: WF_CHECKPOINTING__STAGES).",
    )

    # -- PII
    pii_query_egress: str = Field(
        default="hash_with_session_key",
        description="PII on query egress (env: WF_PII__QUERY_EGRESS).",
    )
    pii_evidence_ingest: str = Field(
        default="mask",
        description="PII on evidence ingest (env: WF_PII__EVIDENCE_INGEST).",
    )
    pii_checkpoint_write: str = Field(
        default="mask",
        description="PII on checkpoint write "
        "(env: WF_PII__CHECKPOINT_WRITE).",
    )
    pii_pre_synthesis: str = Field(
        default="mask",
        description="PII before synthesis (env: WF_PII__PRE_SYNTHESIS).",
    )
