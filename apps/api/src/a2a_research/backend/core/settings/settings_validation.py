"""Settings validation helpers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings

__all__ = ["expected_prefixed_keys", "validate_dotenv_keys"]

_PASSTHROUGH_PREFIXES = ("WF_",)


def expected_prefixed_keys(settings_cls: type[BaseSettings]) -> set[str]:
    prefix = str(settings_cls.model_config.get("env_prefix") or "").upper()
    return {f"{prefix}{name}".upper() for name in settings_cls.model_fields}


def validate_dotenv_keys(expected_keys: set[str]) -> None:
    """Warn about unknown .env keys."""
    from a2a_research.backend.core.settings import ENV_FILE, dotenv_values

    raw_values = dotenv_values(ENV_FILE)
    unknown_keys: list[str] = []

    for key in raw_values:
        normalized = key.upper()
        if normalized in expected_keys:
            continue
        if any(normalized.startswith(p) for p in _PASSTHROUGH_PREFIXES):
            continue
        unknown_keys.append(key)

    if unknown_keys:
        rendered = ", ".join(sorted(unknown_keys))
        logging.getLogger(__name__).warning(
            "Unknown keys in .env: %s. "
            "Allowed keys: LOG_LEVEL, "
            "WORKFLOW_TIMEOUT, TAVILY_API_KEY, "
            "BRAVE_API_KEY, SEARCH_MAX_RESULTS, "
            "SEARCHER_MAX_STEPS, RESEARCH_MAX_ROUNDS, "
            "LLM_*, WF_*, service *_PORT / *_URL.",
            rendered,
        )
