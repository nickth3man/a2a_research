"""Workflow budget, search, and ranking configuration mixin."""

from __future__ import annotations

from pydantic import Field


class BudgetSearchRankingMixin:
    """Mixin providing budget, search, and ranking fields."""

    # -- Budget
    budget_max_rounds: int = Field(
        default=5,
        ge=1,
        description="Max planner rounds (env: WF_BUDGET__MAX_ROUNDS).",
    )
    budget_max_tokens: int = Field(
        default=200_000,
        ge=1_000,
        description="Token budget (env: WF_BUDGET__MAX_TOKENS).",
    )
    budget_max_wall_seconds: int = Field(
        default=180,
        ge=10,
        description="Wall-clock budget seconds "
        "(env: WF_BUDGET__MAX_WALL_SECONDS).",
    )
    budget_max_http_calls: int = Field(
        default=50,
        ge=1,
        description="Outbound HTTP cap (env: WF_BUDGET__MAX_HTTP_CALLS).",
    )
    budget_min_marginal_evidence: int = Field(
        default=2,
        ge=0,
        description="Min new evidence to continue "
        "(env: WF_BUDGET__MIN_MARGINAL_EVIDENCE).",
    )
    budget_max_critic_revision_loops: int = Field(
        default=2,
        ge=0,
        description="Critic loops before synthesis "
        "(env: WF_BUDGET__MAX_CRITIC_REVISION_LOOPS).",
    )

    # -- Search
    search_providers: list[str] = Field(
        default=["tavily", "brave", "ddg"],
        description="Ordered search providers (env: WF_SEARCH__PROVIDERS).",
    )
    search_parallel: bool = Field(
        default=True,
        description="Run provider queries concurrently "
        "(env: WF_SEARCH__PARALLEL).",
    )
    search_max_results_per_provider: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Cap per provider response "
        "(env: WF_SEARCH__MAX_RESULTS_PER_PROVIDER).",
    )

    # -- Ranking
    ranking_enabled: bool = Field(
        default=True,
        description="Enable ranking (env: WF_RANKING__ENABLED).",
    )
    ranking_fetch_budget: int = Field(
        default=8,
        ge=1,
        description="Pages to fetch for ranking "
        "(env: WF_RANKING__FETCH_BUDGET).",
    )
    ranking_diversity_penalty: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="MMR diversity penalty "
        "(env: WF_RANKING__DIVERSITY_PENALTY).",
    )
    ranking_freshness_weight_default: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Freshness weight (env: "
        "WF_RANKING__FRESHNESS_WEIGHT_DEFAULT).",
    )
