"""Core application settings and validation."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from a2a_research.settings_core_agents import AgentEndpointsMixin
from a2a_research.settings_dotenv_keys import _EXPECTED_DOTENV_KEYS
from a2a_research.settings_llm import LLMSettings
from a2a_research.settings_validation import _validate_dotenv_keys
from a2a_research.settings_workflow import WorkflowConfig

__all__ = ["AppSettings"]


def _build_llm_settings() -> LLMSettings:
    from a2a_research.settings import _ENV_FILE

    return LLMSettings(
        _env_file=str(_ENV_FILE)  # type: ignore[call-arg]
    )


def _build_workflow_settings() -> WorkflowConfig:
    from a2a_research.settings import _ENV_FILE

    return WorkflowConfig(
        _env_file=str(_ENV_FILE)  # type: ignore[call-arg]
    )


class AppSettings(AgentEndpointsMixin, BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **data: Any) -> None:
        from a2a_research.settings import _ENV_FILE

        super().__init__(_env_file=str(_ENV_FILE), **data)

    log_level: str = Field(
        default="DEBUG",
        description="Logging threshold (env: LOG_LEVEL).",
    )
    mesop_port: int = Field(
        default=32123,
        description="Mesop UI port (env: MESOP_PORT).",
    )
    workflow_timeout: float = Field(
        default=180.0,
        description="Workflow timeout seconds (env: WORKFLOW_TIMEOUT).",
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
    def validate_dotenv_contract(self) -> "AppSettings":
        _validate_dotenv_keys(_EXPECTED_DOTENV_KEYS)
        return self

    @model_validator(mode="after")
    def require_api_credentials(self) -> "AppSettings":
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
