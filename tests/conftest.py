"""Shared fixtures and global singleton reset."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load repo ``.env`` first so real keys win over the placeholders below. Pytest
# imports this module before ``a2a_research.settings``; without this,
# ``setdefault`` would pin test placeholders and override ``.env`` for
# Pydantic.
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_FILE)

# :mod:`a2a_research.settings` loads a singleton on import; credentials must
# exist first.
os.environ.setdefault("LLM_API_KEY", "test-llm-key-placeholder")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key-placeholder")
os.environ.setdefault("BRAVE_API_KEY", "test-brave-key-placeholder")


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def reset_global_singletons():
    """Reset module-level singletons between tests to prevent state leakage."""
    from a2a_research.backend.core.a2a import reset_registry
    from a2a_research.backend.llm.providers import reset_provider_singletons

    reset_provider_singletons()
    reset_registry()
    yield
    reset_provider_singletons()
    reset_registry()
