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
