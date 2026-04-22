"""Workflow configuration and runtime models.

Models for budget tracking, retry policies, circuit breakers, and agent
definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from a2a_research.backend.core.models.enums import (
        AgentCapability,
        AgentRole,
    )


@dataclass
class BudgetConsumption:
    """Multi-dimensional budget tracking."""

    rounds: int = 0
    tokens_consumed: int = 0
    wall_seconds: float = 0.0
    http_calls: int = 0
    urls_fetched: int = 0
    critic_revision_loops: int = 0

    def is_exhausted(self, budget: WorkflowBudget) -> bool:
        """Return True if any budget dimension is exhausted."""
        return (
            self.rounds >= budget.max_rounds
            or self.tokens_consumed >= budget.max_tokens
            or self.wall_seconds >= budget.max_wall_seconds
            or self.http_calls >= budget.max_http_calls
            or self.critic_revision_loops >= budget.max_critic_revision_loops
        )


@dataclass
class NoveltyTracker:
    """Tracks novelty of evidence across rounds."""

    new_unique_hits: int = 0
    new_unique_pages: int = 0
    new_supporting_evidence_spans: int = 0
    new_independent_publishers: int = 0

    @property
    def marginal_gain(self) -> int:
        """Weighted score of new evidence discovered."""
        return (
            self.new_unique_hits
            + self.new_unique_pages
            + self.new_supporting_evidence_spans
            + 2 * self.new_independent_publishers
        )


@dataclass
class RetryPolicy:
    """Retry configuration for agent calls."""

    max_attempts: int = 3
    backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0


@dataclass
class AgentDefinition:
    """Runtime contract for an agent role."""

    role: AgentRole
    capabilities: set[AgentCapability] = field(default_factory=set)
    input_schema: type[BaseModel] | None = None
    output_schema: type[BaseModel] | None = None
    url_env_var: str = ""
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    circuit_breaker: CircuitBreakerConfig | None = None


class WorkflowBudget(BaseModel):
    """Budget constraints for the workflow."""

    max_rounds: int = 5
    max_tokens: int = 200000
    max_wall_seconds: float = 180.0
    max_http_calls: int = 50
    max_urls_fetched: int = 20
    min_marginal_evidence: int = 2
    max_critic_revision_loops: int = 2
