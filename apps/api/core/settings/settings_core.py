"""Core application settings and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .settings_core_agents import AgentEndpointsMixin
from .settings_dotenv_keys import EXPECTED_DOTENV_KEYS
from .settings_llm import LLMSettings
from .settings_validation import validate_dotenv_keys
from .settings_workflow import WorkflowConfig

__all__ = ["AppSettings"]


def _env_file() -> Path:
    return Path(__file__).resolve().parents[4] / ".env"


def _build_llm_settings() -> LLMSettings:
    return cast(
        "LLMSettings", cast("Any", LLMSettings)(_env_file=str(_env_file()))
    )


def _build_workflow_settings() -> WorkflowConfig:
    return cast(
        "WorkflowConfig",
        cast("Any", WorkflowConfig)(_env_file=str(_env_file())),
    )


class AppSettings(AgentEndpointsMixin, BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **data: Any) -> None:
        super().__init__(_env_file=str(_env_file()), **data)

    log_level: str = Field(
        default="DEBUG",
        description="Logging threshold (env: LOG_LEVEL).",
    )
    workflow_timeout: float = Field(
        default=180.0,
        description="Workflow timeout seconds (env: WORKFLOW_TIMEOUT).",
    )
    api_key: str = Field(
        default="",
        description=(
            "Optional gateway API key (env: API_KEY). When set, "
            "research endpoints require the X-API-Key header."
        ),
    )
    max_concurrent_sessions: int = Field(
        default=5,
        ge=1,
        le=100,
        description=(
            "Maximum concurrently running research sessions "
            "(env: MAX_CONCURRENT_SESSIONS)."
        ),
    )
    session_ttl_seconds: float = Field(
        default=900.0,
        ge=30.0,
        description=(
            "Seconds to retain completed or abandoned research sessions "
            "before pruning (env: SESSION_TTL_SECONDS)."
        ),
    )
    tavily_api_key: str = Field(
        default="",
        description="Tavily API key (env: TAVILY_API_KEY).",
    )
    brave_api_key: str = Field(
        default="",
        description="Brave API key (env: BRAVE_API_KEY).",
    )
    search_max_results: int = Field(
        default=5,
        ge=1,
        le=25,
        description="Per-provider fetch cap (env: SEARCH_MAX_RESULTS).",
    )
    searcher_max_steps: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Searcher tool steps (env: SEARCHER_MAX_STEPS).",
    )
    research_max_rounds: int = Field(
        default=5,
        ge=1,
        le=10,
        description="FactChecker rounds (env: RESEARCH_MAX_ROUNDS).",
    )

    llm: LLMSettings = Field(default_factory=_build_llm_settings)
    workflow: WorkflowConfig = Field(default_factory=_build_workflow_settings)

    @model_validator(mode="after")
    def validate_dotenv_contract(self) -> AppSettings:
        validate_dotenv_keys(EXPECTED_DOTENV_KEYS)
        return self

    @model_validator(mode="after")
    def require_api_credentials(self) -> AppSettings:
        if not self.llm.api_key.strip():
            msg = "LLM_API_KEY required — set in .env or env."
            raise ValueError(msg)
        if not self.tavily_api_key.strip():
            msg = "TAVILY_API_KEY required — set in .env or env."
            raise ValueError(msg)
        if not self.brave_api_key.strip():
            msg = "BRAVE_API_KEY required — set in .env or env."
            raise ValueError(msg)
        return self
