"""Cover main_page branches with stub Mesop box runtime."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from a2a_research.models import AgentResult, AgentRole, AgentStatus, ResearchSession
from a2a_research.ui.session_state import has_results


@pytest.fixture
def stub_mesop_box_runtime() -> None:
    """Stub `me.box` tree used by main_page and nested components."""
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
    with patch("mesop.component_helpers.helper.runtime", return_value=rt):
        yield


def _make_state(**kwargs: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "query_text": "",
        "error": None,
        "loading": False,
        "session": ResearchSession(),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.usefixtures("stub_mesop_box_runtime")
def test_main_page_empty_state() -> None:
    from a2a_research.ui import app as app_mod

    st = _make_state()
    with patch("a2a_research.ui.app.me.state", return_value=st):
        app_mod.main_page()


@pytest.mark.usefixtures("stub_mesop_box_runtime")
def test_main_page_shows_error_banner() -> None:
    from a2a_research.ui import app as app_mod

    st = _make_state(error="Something broke")
    with patch("a2a_research.ui.app.me.state", return_value=st):
        app_mod.main_page()


@pytest.mark.usefixtures("stub_mesop_box_runtime")
def test_main_page_loading() -> None:
    from a2a_research.ui import app as app_mod

    st = _make_state(
        loading=True,
        session=ResearchSession(query="Q"),
    )
    with patch("a2a_research.ui.app.me.state", return_value=st):
        app_mod.main_page()


@pytest.mark.usefixtures("stub_mesop_box_runtime")
def test_main_page_results() -> None:
    from a2a_research.ui import app as app_mod

    session = ResearchSession(
        query="Q",
        agent_results={
            AgentRole.PRESENTER: AgentResult(
                role=AgentRole.PRESENTER,
                status=AgentStatus.COMPLETED,
            ),
        },
        final_report="# OK",
    )
    assert has_results(session)
    st = _make_state(session=session)
    with patch("a2a_research.ui.app.me.state", return_value=st):
        app_mod.main_page()


def test_app_state_uses_default_session_factory() -> None:
    from a2a_research.ui import app as app_mod

    st = app_mod.AppState()
    assert isinstance(st.session, ResearchSession)
    assert st.session.query == ""
