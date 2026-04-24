"""Typed application settings loaded from ``.env`` and environment.

This module re-exports from split sub-modules for backward compatibility.

Prefixes (Pydantic ``BaseSettings``):

- ``LLM_*`` — OpenRouter model id, base URL, API key.

Unprefixed fields on :class:`AppSettings`: ``LOG_LEVEL``,
``WORKFLOW_TIMEOUT``, ``TAVILY_API_KEY`` and ``BRAVE_API_KEY`` (required),
``SEARCH_MAX_RESULTS``, ``SEARCHER_MAX_STEPS``, ``RESEARCH_MAX_ROUNDS``,
``*_PORT``, ``*_URL``.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values

from .settings_core import AppSettings
from .settings_dotenv_keys import EXPECTED_DOTENV_KEYS
from .settings_llm import LLMSettings
from .settings_validation import validate_dotenv_keys as _vd
from .settings_workflow import WorkflowConfig

_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_ENV_FILE = _PROJECT_ROOT / ".env"
ENV_FILE = _ENV_FILE


def _validate_dotenv_keys() -> None:
    validate_dotenv_keys()


def validate_dotenv_keys() -> None:
    _vd(EXPECTED_DOTENV_KEYS)


settings = AppSettings()

__all__ = [
    "ENV_FILE",
    "_ENV_FILE",
    "AppSettings",
    "LLMSettings",
    "WorkflowConfig",
    "_validate_dotenv_keys",
    "dotenv_values",
    "settings",
    "validate_dotenv_keys",
]
