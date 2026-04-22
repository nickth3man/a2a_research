"""Tests for Mesop app query input handler (mocked Mesop)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

from tests.ui_app_helpers import _make_state

if TYPE_CHECKING:
    from mesop.events import InputEvent


def test_on_query_input_updates_state() -> None:
    from a2a_research.ui import app as app_mod

    st = _make_state()
    ev = cast("InputEvent", SimpleNamespace(value="  hello "))
    with patch.object(app_mod.me, "state", return_value=st):
        app_mod._on_query_input(ev)
    assert st.query_text == "  hello "
