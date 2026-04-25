"""Workflow A/B testing configuration mixin."""

from __future__ import annotations

from pydantic import Field, field_validator


class ABTestingMixin:
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
        default={
            "claim_recall": 0.35,
            "citation_accuracy": 0.35,
            "latency": 0.15,
            "cost": 0.15,
        },
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
