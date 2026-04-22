"""Default values for WorkflowConfigExt."""

from __future__ import annotations

DEFAULT_OUTPUT_FORMATS: list[str] = ["markdown", "json"]

DEFAULT_CHECKPOINT_STAGES: list[str] = [
    "plan",
    "verify",
    "adversary_gate",
    "synthesize",
]

DEFAULT_TELEMETRY_TRACE_IDS: list[str] = [
    "session_id",
    "trace_id",
    "span_id",
]

DEFAULT_COST_ATTRIBUTION_TAGS: list[str] = [
    "session_id",
    "claim_id",
    "user_id",
]

DEFAULT_AB_TESTING_WEIGHTS: dict[str, float] = {
    "claim_recall": 0.35,
    "citation_accuracy": 0.35,
    "latency": 0.15,
    "cost": 0.15,
}
