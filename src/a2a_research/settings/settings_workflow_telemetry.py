"""Workflow telemetry and cost attribution configuration mixin."""

from __future__ import annotations

from pydantic import Field


class TelemetryMixin:
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
        default=["session_id", "trace_id", "span_id"],
        description="IDs per span (env: WF_TELEMETRY__TRACE_IDS).",
    )

    cost_attribution_enabled: bool = Field(
        default=True,
        description="Cost attribution (env: WF_COST_ATTRIBUTION__ENABLED).",
    )
    cost_attribution_tags: list[str] = Field(
        default=["session_id", "claim_id", "user_id"],
        description="Cost tags (env: WF_COST_ATTRIBUTION__TAGS).",
    )
