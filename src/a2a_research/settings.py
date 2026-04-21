"""Typed application settings loaded from the project ``.env`` and environment.

Prefixes (Pydantic ``BaseSettings``):

- ``LLM_*`` — OpenRouter model id, base URL, API key.

Unprefixed fields on :class:`AppSettings`: ``LOG_LEVEL``, ``MESOP_PORT``,
``WORKFLOW_TIMEOUT``, ``TAVILY_API_KEY`` and ``BRAVE_API_KEY`` (required),
``SEARCH_MAX_RESULTS``,
``SEARCHER_MAX_STEPS``, ``RESEARCH_MAX_ROUNDS``, ``*_PORT``, ``*_URL``.
``LLM_PROVIDER`` is accepted in ``.env`` for backward compatibility but is
ignored (all LLM traffic uses :class:`LLMSettings` / OpenRouter-style vars).

Mesop reads additional ``MESOP_*`` variables (for example
``MESOP_STATE_SESSION_BACKEND``) via its own library config.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"

__all__ = ["AppSettings", "LLMSettings", "WorkflowConfig", "settings"]


class LLMSettings(BaseSettings):
    """OpenRouter configuration used by every LLM integration."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        extra="ignore",
    )

    model: str = Field(
        default="openrouter/elephant-alpha",
        description="OpenRouter model identifier.",
    )
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter base URL.",
    )
    api_key: str = Field(
        default="",
        description="OpenRouter API key (required when using AppSettings; env: LLM_API_KEY).",
    )


class WorkflowConfig(BaseSettings):
    """Comprehensive workflow orchestration configuration (env prefix: ``WF_``).

    Every field maps to ``WF_<SECTION>_<FIELD>`` in the environment (e.g.
    ``WF_BUDGET_MAX_ROUNDS``, ``WF_SEARCH_PROVIDERS``).  Nested models flatten
    automatically via *pydantic-settings*.
    """

    model_config = SettingsConfigDict(
        env_prefix="WF_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Budget ────────────────────────────────────────────────────────────
    budget_max_rounds: int = Field(
        default=5,
        ge=1,
        description="Maximum planner→verify→synthesize rounds (env: WF_BUDGET__MAX_ROUNDS).",
    )
    budget_max_tokens: int = Field(
        default=200_000,
        ge=1_000,
        description="Token budget across all LLM calls (env: WF_BUDGET__MAX_TOKENS).",
    )
    budget_max_wall_seconds: int = Field(
        default=180,
        ge=10,
        description="Wall-clock budget in seconds (env: WF_BUDGET__MAX_WALL_SECONDS).",
    )
    budget_max_http_calls: int = Field(
        default=50,
        ge=1,
        description="Upper bound on outbound HTTP requests (env: WF_BUDGET__MAX_HTTP_CALLS).",
    )
    budget_min_marginal_evidence: int = Field(
        default=2,
        ge=0,
        description="Minimum new evidence items to continue another round (env: WF_BUDGET__MIN_MARGINAL_EVIDENCE).",
    )
    budget_max_critic_revision_loops: int = Field(
        default=2,
        ge=0,
        description="Critic revision iterations before forcing synthesis (env: WF_BUDGET__MAX_CRITIC_REVISION_LOOPS).",
    )

    # ── Search ────────────────────────────────────────────────────────────
    search_providers: list[str] = Field(
        default=["tavily", "brave", "ddg"],
        description="Ordered list of search providers (env: WF_SEARCH__PROVIDERS).",
    )
    search_parallel: bool = Field(
        default=True,
        description="Run provider queries concurrently (env: WF_SEARCH__PARALLEL).",
    )
    search_max_results_per_provider: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Cap per provider response (env: WF_SEARCH__MAX_RESULTS_PER_PROVIDER).",
    )

    # ── Ranking ───────────────────────────────────────────────────────────
    ranking_enabled: bool = Field(
        default=True,
        description="Enable result ranking stage (env: WF_RANKING__ENABLED).",
    )
    ranking_fetch_budget: int = Field(
        default=8,
        ge=1,
        description="Max pages to fetch for ranking (env: WF_RANKING__FETCH_BUDGET).",
    )
    ranking_diversity_penalty: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="MMR-style diversity penalty (env: WF_RANKING__DIVERSITY_PENALTY).",
    )
    ranking_freshness_weight_default: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Default freshness weight for recency scoring (env: WF_RANKING__FRESHNESS_WEIGHT_DEFAULT).",
    )

    # ── Evidence ──────────────────────────────────────────────────────────
    evidence_deduplication: bool = Field(
        default=True,
        description="Deduplicate evidence chunks (env: WF_EVIDENCE__DEDUPLICATION).",
    )
    evidence_chunk_size: int = Field(
        default=1000,
        ge=100,
        description="Chunk size in characters for evidence splitting (env: WF_EVIDENCE__CHUNK_SIZE).",
    )
    evidence_chunk_overlap: int = Field(
        default=200,
        ge=0,
        description="Overlap between consecutive chunks (env: WF_EVIDENCE__CHUNK_OVERLAP).",
    )
    evidence_source_independence: bool = Field(
        default=True,
        description="Track whether evidence comes from independent sources (env: WF_EVIDENCE__SOURCE_INDEPENDENCE).",
    )

    # ── Adversary ─────────────────────────────────────────────────────────
    adversary_enabled: bool = Field(
        default=True,
        description="Enable adversary challenge stage (env: WF_ADVERSARY__ENABLED).",
    )
    adversary_trigger: str = Field(
        default="on_tentative_supported",
        description="When to invoke the adversary (env: WF_ADVERSARY__TRIGGER).",
    )
    adversary_inversion_query_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of counter-query inversions (env: WF_ADVERSARY__INVERSION_QUERY_COUNT).",
    )
    adversary_counter_expert_lookup: bool = Field(
        default=True,
        description="Search for counter-expert opinions (env: WF_ADVERSARY__COUNTER_EXPERT_LOOKUP).",
    )

    # ── Verification ──────────────────────────────────────────────────────
    verification_cache_results: bool = Field(
        default=True,
        description="Cache verification results (env: WF_VERIFICATION__CACHE_RESULTS).",
    )
    verification_confidence_auto_accept_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Auto-accept claims at or above this confidence (env: WF_VERIFICATION__CONFIDENCE_AUTO_ACCEPT_THRESHOLD).",
    )
    verification_short_circuit_when_adversary_holds: bool = Field(
        default=True,
        description="Skip further rounds if adversary holds (env: WF_VERIFICATION__SHORT_CIRCUIT_WHEN_ADVERSARY_HOLDS).",
    )

    # ── Synthesis ─────────────────────────────────────────────────────────
    synthesis_streaming: str = Field(
        default="sse_via_coordinator",
        description="Streaming mode for synthesis output (env: WF_SYNTHESIS__STREAMING).",
    )
    synthesis_tentative_snapshot_strategy: str = Field(
        default="cheap_template_every_round_plus_full_on_exit",
        description="Snapshot strategy for tentative results (env: WF_SYNTHESIS__TENTATIVE_SNAPSHOT_STRATEGY).",
    )

    # ── Output ────────────────────────────────────────────────────────────
    output_formats: list[str] = Field(
        default=["markdown", "json"],
        description="Allowed output formats (env: WF_OUTPUT__FORMATS).",
    )
    output_citation_style: str = Field(
        default="hyperlinked_footnotes",
        description="Citation rendering style (env: WF_OUTPUT__CITATION_STYLE).",
    )

    # ── Checkpointing ─────────────────────────────────────────────────────
    checkpointing_enabled: bool = Field(
        default=True,
        description="Enable stage checkpointing (env: WF_CHECKPOINTING__ENABLED).",
    )
    checkpointing_stages: list[str] = Field(
        default=["plan", "verify", "adversary_gate", "synthesize"],
        description="Stages at which to persist checkpoints (env: WF_CHECKPOINTING__STAGES).",
    )

    # ── PII ───────────────────────────────────────────────────────────────
    pii_query_egress: str = Field(
        default="hash_with_session_key",
        description="PII handling on query egress (env: WF_PII__QUERY_EGRESS).",
    )
    pii_evidence_ingest: str = Field(
        default="mask",
        description="PII handling on evidence ingest (env: WF_PII__EVIDENCE_INGEST).",
    )
    pii_checkpoint_write: str = Field(
        default="mask",
        description="PII handling on checkpoint write (env: WF_PII__CHECKPOINT_WRITE).",
    )
    pii_pre_synthesis: str = Field(
        default="mask",
        description="PII handling before synthesis (env: WF_PII__PRE_SYNTHESIS).",
    )

    # ── Telemetry ─────────────────────────────────────────────────────────
    telemetry_opentelemetry: bool = Field(
        default=True,
        description="Enable OpenTelemetry traces (env: WF_TELEMETRY__OPENTELEMETRY).",
    )
    telemetry_prometheus: bool = Field(
        default=True,
        description="Enable Prometheus metrics (env: WF_TELEMETRY__PROMETHEUS).",
    )
    telemetry_trace_log: bool = Field(
        default=True,
        description="Write structured trace log (env: WF_TELEMETRY__TRACE_LOG).",
    )
    telemetry_trace_ids: list[str] = Field(
        default=["session_id", "trace_id", "span_id"],
        description="IDs attached to every telemetry span (env: WF_TELEMETRY__TRACE_IDS).",
    )

    # ── Cost Attribution ──────────────────────────────────────────────────
    cost_attribution_enabled: bool = Field(
        default=True,
        description="Enable per-query cost attribution (env: WF_COST_ATTRIBUTION__ENABLED).",
    )
    cost_attribution_tags: list[str] = Field(
        default=["session_id", "claim_id", "user_id"],
        description="Tags attached to cost records (env: WF_COST_ATTRIBUTION__TAGS).",
    )

    # ── A/B Testing ───────────────────────────────────────────────────────
    ab_testing_enabled: bool = Field(
        default=True,
        description="Enable A/B testing (env: WF_AB_TESTING__ENABLED).",
    )
    ab_testing_sampling: str = Field(
        default="per_query_class_sticky",
        description="A/B sampling strategy (env: WF_AB_TESTING__SAMPLING).",
    )
    ab_testing_winner_metric: str = Field(
        default="weighted_composite",
        description="Metric for choosing the winning variant (env: WF_AB_TESTING__WINNER_METRIC).",
    )
    ab_testing_weights: dict[str, float] = Field(
        default={
            "claim_recall": 0.35,
            "citation_accuracy": 0.35,
            "latency": 0.15,
            "cost": 0.15,
        },
        description="Weights for the weighted_composite metric (env: WF_AB_TESTING__WEIGHTS).",
    )

    @field_validator("ab_testing_weights")
    @classmethod
    def _weights_must_sum_to_one(cls, v: dict[str, float]) -> dict[str, float]:
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            msg = f"ab_testing_weights must sum to ~1.0, got {total:.4f}"
            raise ValueError(msg)
        return v


def _expected_prefixed_keys(settings_cls: type[BaseSettings]) -> set[str]:
    prefix = str(settings_cls.model_config.get("env_prefix") or "").upper()
    return {f"{prefix}{name}".upper() for name in settings_cls.model_fields}


_EXPECTED_DOTENV_KEYS = {
    # Legacy from older templates; not read by Pydantic (kept to avoid noisy warnings).
    "LLM_PROVIDER",
    "LOG_LEVEL",
    "MESOP_PORT",
    "WORKFLOW_TIMEOUT",
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
    "SEARCH_MAX_RESULTS",
    "SEARCHER_MAX_STEPS",
    "RESEARCH_MAX_ROUNDS",
    "PREPROCESSOR_PORT",
    "CLARIFIER_PORT",
    "PLANNER_PORT",
    "SEARCHER_PORT",
    "RANKER_PORT",
    "READER_PORT",
    "EVIDENCE_DEDUPLICATOR_PORT",
    "FACT_CHECKER_PORT",
    "ADVERSARY_PORT",
    "SYNTHESIZER_PORT",
    "CRITIC_PORT",
    "POSTPROCESSOR_PORT",
    "PREPROCESSOR_URL",
    "CLARIFIER_URL",
    "PLANNER_URL",
    "SEARCHER_URL",
    "RANKER_URL",
    "READER_URL",
    "EVIDENCE_DEDUPLICATOR_URL",
    "FACT_CHECKER_URL",
    "ADVERSARY_URL",
    "SYNTHESIZER_URL",
    "CRITIC_URL",
    "POSTPROCESSOR_URL",
    *_expected_prefixed_keys(LLMSettings),
    *_expected_prefixed_keys(WorkflowConfig),
}

_PASSTHROUGH_PREFIXES = ("MESOP_", "WF_")


def _build_llm_settings() -> LLMSettings:
    return LLMSettings(_env_file=str(_ENV_FILE))  # type: ignore[call-arg]  # ty: ignore[unknown-argument]


def _build_workflow_settings() -> WorkflowConfig:
    return WorkflowConfig(_env_file=str(_ENV_FILE))  # type: ignore[call-arg]  # ty: ignore[unknown-argument]


def _validate_dotenv_keys() -> None:
    """Warn about unknown keys in .env without failing (supports shared environments)."""
    raw_values = dotenv_values(_ENV_FILE)
    unknown_keys: list[str] = []

    for key in raw_values:
        normalized = key.upper()

        if normalized in _EXPECTED_DOTENV_KEYS:
            continue

        if any(
            normalized.startswith(prefix) for prefix in _PASSTHROUGH_PREFIXES
        ):
            continue

        unknown_keys.append(key)

    if unknown_keys:
        rendered = ", ".join(sorted(unknown_keys))
        logging.getLogger(__name__).warning(
            "Unknown keys in .env: %s. "
            "Allowed project keys are LOG_LEVEL, MESOP_PORT, WORKFLOW_TIMEOUT, "
            "TAVILY_API_KEY, BRAVE_API_KEY, SEARCH_MAX_RESULTS, SEARCHER_MAX_STEPS, RESEARCH_MAX_ROUNDS, "
            "LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, LLM_PROVIDER (ignored legacy), "
            "WF_* keys (workflow config), "
            "service *_PORT / *_URL keys. "
            "MESOP_* keys are allowed as passthrough.",
            rendered,
        )


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(_env_file=str(_ENV_FILE), **data)

    log_level: str = Field(
        default="DEBUG",
        description=(
            "Logging threshold for console and every file under logs/ (env: LOG_LEVEL). "
            "Standard names: DEBUG, INFO, WARNING, ERROR."
        ),
    )
    mesop_port: int = Field(
        default=32123,
        description="Default port for the Mesop UI in app tooling (env: MESOP_PORT).",
    )
    workflow_timeout: float = Field(
        default=180.0,
        description="Maximum workflow runtime in seconds before returning a partial timed-out session.",
    )
    tavily_api_key: str = Field(
        default="",
        description="Tavily API key for web search (required; env: TAVILY_API_KEY).",
    )
    brave_api_key: str = Field(
        default="",
        description="Brave Search API key (required; env: BRAVE_API_KEY).",
    )
    search_max_results: int = Field(
        default=5,
        ge=1,
        le=25,
        description=(
            "Per-provider fetch cap for parallel Tavily + Brave + DDG; merged list is capped "
            "separately (env: SEARCH_MAX_RESULTS)."
        ),
    )
    searcher_max_steps: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max tool-calling steps for the smolagents Searcher agent (env: SEARCHER_MAX_STEPS).",
    )
    research_max_rounds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum number of FactChecker loop rounds (env: RESEARCH_MAX_ROUNDS).",
    )
    preprocessor_port: int = Field(
        default=10006, description="Preprocessor HTTP A2A port."
    )
    clarifier_port: int = Field(
        default=10007, description="Clarifier HTTP A2A port."
    )
    planner_port: int = Field(
        default=10001, description="Planner HTTP A2A port."
    )
    searcher_port: int = Field(
        default=10002, description="Searcher HTTP A2A port."
    )
    ranker_port: int = Field(
        default=10008, description="Ranker HTTP A2A port."
    )
    reader_port: int = Field(
        default=10003, description="Reader HTTP A2A port."
    )
    evidence_deduplicator_port: int = Field(
        default=10009, description="EvidenceDeduplicator HTTP A2A port."
    )
    fact_checker_port: int = Field(
        default=10004, description="FactChecker HTTP A2A port."
    )
    adversary_port: int = Field(
        default=10010, description="Adversary HTTP A2A port."
    )
    synthesizer_port: int = Field(
        default=10005, description="Synthesizer HTTP A2A port."
    )
    critic_port: int = Field(
        default=10011, description="Critic HTTP A2A port."
    )
    postprocessor_port: int = Field(
        default=10012, description="Postprocessor HTTP A2A port."
    )
    preprocessor_url: str = Field(
        default="http://localhost:10006",
        description="Preprocessor HTTP A2A URL.",
    )
    clarifier_url: str = Field(
        default="http://localhost:10007", description="Clarifier HTTP A2A URL."
    )
    planner_url: str = Field(
        default="http://localhost:10001", description="Planner HTTP A2A URL."
    )
    searcher_url: str = Field(
        default="http://localhost:10002", description="Searcher HTTP A2A URL."
    )
    ranker_url: str = Field(
        default="http://localhost:10008", description="Ranker HTTP A2A URL."
    )
    reader_url: str = Field(
        default="http://localhost:10003", description="Reader HTTP A2A URL."
    )
    evidence_deduplicator_url: str = Field(
        default="http://localhost:10009",
        description="EvidenceDeduplicator HTTP A2A URL.",
    )
    fact_checker_url: str = Field(
        default="http://localhost:10004",
        description="FactChecker HTTP A2A URL.",
    )
    adversary_url: str = Field(
        default="http://localhost:10010", description="Adversary HTTP A2A URL."
    )
    synthesizer_url: str = Field(
        default="http://localhost:10005",
        description="Synthesizer HTTP A2A URL.",
    )
    critic_url: str = Field(
        default="http://localhost:10011", description="Critic HTTP A2A URL."
    )
    postprocessor_url: str = Field(
        default="http://localhost:10012",
        description="Postprocessor HTTP A2A URL.",
    )

    llm: LLMSettings = Field(default_factory=_build_llm_settings)
    workflow: WorkflowConfig = Field(default_factory=_build_workflow_settings)

    @model_validator(mode="after")
    def validate_dotenv_contract(self) -> AppSettings:
        _validate_dotenv_keys()
        return self

    @model_validator(mode="after")
    def require_api_credentials(self) -> AppSettings:
        if not self.llm.api_key.strip():
            msg = (
                "LLM_API_KEY is required — set it in .env or the environment."
            )
            raise ValueError(msg)
        if not self.tavily_api_key.strip():
            msg = "TAVILY_API_KEY is required — set it in .env or the environment."
            raise ValueError(msg)
        if not self.brave_api_key.strip():
            msg = "BRAVE_API_KEY is required — set it in .env or the environment."
            raise ValueError(msg)
        return self


settings = AppSettings()
