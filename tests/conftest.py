"""Shared fixtures: Mesop runtime stubs + global singleton reset."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from mesop.component_helpers import helper  # noqa: E402


@pytest.fixture
def stub_mesop_component_runtime() -> None:
    """Stub ``helper.runtime()`` for ``@me.component`` and page layout"""
    """trees."""
    node = MagicMock()
    child = MagicMock()
    child.MergeFrom = MagicMock()
    node.children.add.return_value = child
    ctx = MagicMock()
    ctx.current_node.return_value = node
    ctx.set_current_node = MagicMock()
    rt = MagicMock()
    rt.context.return_value = ctx
    rt.debug_mode = False
    with patch.object(helper, "runtime", return_value=rt):
        yield


@pytest.fixture
def stub_mesop_box_runtime(stub_mesop_component_runtime: None) -> None:
    """Alias for main_page tests (same runtime stub as component tests)."""
    yield


@pytest.fixture(autouse=True)
def _reset_global_singletons():
    """Reset module-level singletons between tests to prevent state leakage."""
    from a2a_research.a2a import reset_registry
    from a2a_research.llm.providers import reset_provider_singletons

    reset_provider_singletons()
    reset_registry()
    yield
    reset_provider_singletons()
    reset_registry()
