"""Cover main_page branches with stub Mesop box runtime."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from a2a_research.backend.core.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)
from a2a_research.ui.session_state import has_results


def _make_state(**kwargs: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "query_text": "",
        "error": None,
        "loading": False,
        "session": ResearchSession(),
        "progress_granularity": 1,
        "current_substep": "",
        "progress_pct": 0.0,
        "progress_step_label": "",
        "progress_running_substeps": [],
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
        progress_pct=0.25,
        progress_step_label="Step 1 of 4 — Researcher",
        current_substep="Querying ChromaDB…",
    )
    with patch("a2a_research.ui.app.me.state", return_value=st):
        app_mod.main_page()


@pytest.mark.usefixtures("stub_mesop_box_runtime")
def test_main_page_loading_does_not_render_timeline() -> None:
    from a2a_research.ui import app as app_mod

    st = _make_state(
        loading=True,
        session=ResearchSession(query="Q"),
        progress_pct=0.25,
        progress_step_label="Step 1 of 4 — Researcher",
        current_substep="Querying ChromaDB…",
    )
    with (
        patch("a2a_research.ui.app.me.state", return_value=st),
        patch("a2a_research.ui.page_content.CardLoading") as card_loading,
        patch("a2a_research.ui.page_content.CardTimeline") as card_timeline,
    ):
        app_mod.main_page()

    card_loading.assert_called_once()
    card_timeline.assert_not_called()


@pytest.mark.usefixtures("stub_mesop_box_runtime")
def test_main_page_results() -> None:
    from a2a_research.ui import app as app_mod

    session = ResearchSession(
        query="Q",
        agent_results={
            AgentRole.SYNTHESIZER: AgentResult(
                role=AgentRole.SYNTHESIZER,
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
    from a2a_research.ui.state import AppState

    st = AppState()
    assert isinstance(st.session, ResearchSession)
    assert st.session.query == ""
