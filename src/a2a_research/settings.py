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

from dotenv import dotenv_values
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"

__all__ = ["AppSettings", "LLMSettings", "settings"]


class LLMSettings(BaseSettings):
    """OpenRouter configuration used by every LLM integration."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
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
    "PLANNER_PORT",
    "SEARCHER_PORT",
    "READER_PORT",
    "FACT_CHECKER_PORT",
    "SYNTHESIZER_PORT",
    "PLANNER_URL",
    "SEARCHER_URL",
    "READER_URL",
    "FACT_CHECKER_URL",
    "SYNTHESIZER_URL",
    *_expected_prefixed_keys(LLMSettings),
}

_PASSTHROUGH_PREFIXES = ("MESOP_",)


def _validate_dotenv_keys() -> None:
    """Warn about unknown keys in .env without failing (supports shared environments)."""
    raw_values = dotenv_values(_ENV_FILE)
    unknown_keys: list[str] = []

    for key in raw_values:
        normalized = key.upper()

        if normalized in _EXPECTED_DOTENV_KEYS:
            continue

        if any(normalized.startswith(prefix) for prefix in _PASSTHROUGH_PREFIXES):
            continue

        unknown_keys.append(key)

    if unknown_keys:
        rendered = ", ".join(sorted(unknown_keys))
        logging.getLogger(__name__).warning(
            "Unknown keys in .env: %s. "
            "Allowed project keys are LOG_LEVEL, MESOP_PORT, WORKFLOW_TIMEOUT, "
            "TAVILY_API_KEY, BRAVE_API_KEY, SEARCH_MAX_RESULTS, SEARCHER_MAX_STEPS, RESEARCH_MAX_ROUNDS, "
            "LLM_MODEL, LLM_BASE_URL, LLM_API_KEY, LLM_PROVIDER (ignored legacy), "
            "service *_PORT / *_URL keys. "
            "MESOP_* keys are allowed as passthrough.",
            rendered,
        )


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
    planner_port: int = Field(default=10001, description="Planner HTTP A2A port.")
    searcher_port: int = Field(default=10002, description="Searcher HTTP A2A port.")
    reader_port: int = Field(default=10003, description="Reader HTTP A2A port.")
    fact_checker_port: int = Field(default=10004, description="FactChecker HTTP A2A port.")
    synthesizer_port: int = Field(default=10005, description="Synthesizer HTTP A2A port.")
    planner_url: str = Field(default="http://localhost:10001", description="Planner HTTP A2A URL.")
    searcher_url: str = Field(
        default="http://localhost:10002", description="Searcher HTTP A2A URL."
    )
    reader_url: str = Field(default="http://localhost:10003", description="Reader HTTP A2A URL.")
    fact_checker_url: str = Field(
        default="http://localhost:10004", description="FactChecker HTTP A2A URL."
    )
    synthesizer_url: str = Field(
        default="http://localhost:10005", description="Synthesizer HTTP A2A URL."
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)

    @model_validator(mode="after")
    def validate_dotenv_contract(self) -> AppSettings:
        _validate_dotenv_keys()
        return self

    @model_validator(mode="after")
    def require_api_credentials(self) -> AppSettings:
        if not self.llm.api_key.strip():
            msg = "LLM_API_KEY is required — set it in .env or the environment."
            raise ValueError(msg)
        if not self.tavily_api_key.strip():
            msg = "TAVILY_API_KEY is required — set it in .env or the environment."
            raise ValueError(msg)
        if not self.brave_api_key.strip():
            msg = "BRAVE_API_KEY is required — set it in .env or the environment."
            raise ValueError(msg)
        return self


settings = AppSettings()
