"""Workflow orchestration configuration - Extended settings."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .settings_workflow_ext_defaults import (
    DEFAULT_AB_TESTING_WEIGHTS,
    DEFAULT_CHECKPOINT_STAGES,
    DEFAULT_COST_ATTRIBUTION_TAGS,
    DEFAULT_OUTPUT_FORMATS,
    DEFAULT_TELEMETRY_TRACE_IDS,
)

__all__ = ["WorkflowConfigExt"]


class WorkflowConfigExt(BaseSettings):
    """Extended workflow orchestration config (env prefix: ``WF_``)."""

    model_config = SettingsConfigDict(
        env_prefix="WF_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    output_formats: list[str] = Field(
        default=DEFAULT_OUTPUT_FORMATS,
        description="Allowed output formats (env: WF_OUTPUT__FORMATS).",
    )
    output_citation_style: str = Field(
        default="hyperlinked_footnotes",
        description="Citation style (env: WF_OUTPUT__CITATION_STYLE).",
    )

    checkpointing_enabled: bool = Field(
        default=True,
        description="Enable checkpointing (env: WF_CHECKPOINTING__ENABLED).",
    )
    checkpointing_stages: list[str] = Field(
        default=DEFAULT_CHECKPOINT_STAGES,
        description="Checkpoint stages (env: WF_CHECKPOINTING__STAGES).",
    )

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
        description="PII on checkpoint write (env: WF_PII__CHECKPOINT_WRITE).",
    )
    pii_pre_synthesis: str = Field(
        default="mask",
        description="PII before synthesis (env: WF_PII__PRE_SYNTHESIS).",
    )

    telemetry_opentelemetry: bool = Field(
        default=True,
        description="OpenTelemetry traces (env: WF_TELEMETRY__OPENTELEMETRY).",
    )
    telemetry_prometheus: bool = Field(
        default=True,
        description="Prometheus metrics (env: WF_TELEMETRY__PROMETHEUS).",
    )
    telemetry_trace_log: bool = Field(
        default=True,
        description="Structured trace log (env: WF_TELEMETRY__TRACE_LOG).",
    )
    telemetry_trace_ids: list[str] = Field(
        default=DEFAULT_TELEMETRY_TRACE_IDS,
        description="IDs per span (env: WF_TELEMETRY__TRACE_IDS).",
    )

    cost_attribution_enabled: bool = Field(
        default=True,
        description="Cost attribution (env: WF_COST_ATTRIBUTION__ENABLED).",
    )
    cost_attribution_tags: list[str] = Field(
        default=DEFAULT_COST_ATTRIBUTION_TAGS,
        description="Cost tags (env: WF_COST_ATTRIBUTION__TAGS).",
    )

    ab_testing_enabled: bool = Field(
        default=True,
        description="Enable A/B testing (env: WF_AB_TESTING__ENABLED).",
    )
    ab_testing_sampling: str = Field(
        default="per_query_class_sticky",
        description="Sampling strategy (env: WF_AB_TESTING__SAMPLING).",
    )
    ab_testing_winner_metric: str = Field(
        default="weighted_composite",
        description="Winner metric (env: WF_AB_TESTING__WINNER_METRIC).",
    )
    ab_testing_weights: dict[str, float] = Field(
        default=DEFAULT_AB_TESTING_WEIGHTS,
        description="Composite weights (env: WF_AB_TESTING__WEIGHTS).",
    )

    @field_validator("ab_testing_weights")
    @classmethod
    def _weights_must_sum_to_one(cls, v: dict[str, float]) -> dict[str, float]:
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            msg = f"ab_testing_weights must sum to ~1.0, got {total:.4f}"
            raise ValueError(msg)
        return v
