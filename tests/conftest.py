"""Shared Mesop test doubles (component/box runtime stub)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from mesop.component_helpers import helper


@pytest.fixture
def stub_mesop_component_runtime() -> None:
    """Stub ``helper.runtime()`` for ``@me.component`` and page layout trees."""
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
    from a2a_research.a2a.server import reset_server_registry
    from a2a_research.providers import reset_provider_singletons

    reset_provider_singletons()
    reset_server_registry()

    import a2a_research.rag as rag_module

    rag_module._chroma_client = None
    rag_module._collection = None

    yield

    reset_provider_singletons()
    reset_server_registry()
    rag_module._chroma_client = None
    rag_module._collection = None
