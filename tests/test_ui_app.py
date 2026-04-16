"""Tests for Mesop app handlers (mocked Mesop)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from a2a_research.models import AgentResult, AgentRole, AgentStatus, ResearchSession


def _drain_on_submit(app_mod, mock_event: MagicMock | None = None) -> None:
    gen = app_mod._on_submit(mock_event or MagicMock())
    try:
        next(gen)
    except StopIteration:
        return
    try:
        next(gen)
    except StopIteration:
        return


def test_on_submit_empty_query_sets_error() -> None:
    from a2a_research.ui import app as app_mod

    st = SimpleNamespace(
        query_text="   ",
        error=None,
        loading=False,
        session=ResearchSession(),
    )
    with patch.object(app_mod.me, "state", return_value=st):
        gen = app_mod._on_submit(MagicMock())
        with pytest.raises(StopIteration):
            next(gen)
    assert st.error is not None
    assert "query" in st.error.lower()


def test_on_submit_success_updates_session() -> None:
    from a2a_research.ui import app as app_mod

    done = ResearchSession(
        query="Q",
        agent_results={
            AgentRole.PRESENTER: AgentResult(
                role=AgentRole.PRESENTER,
                status=AgentStatus.COMPLETED,
            ),
        },
        final_report="# Hello",
    )
    st = SimpleNamespace(
        query_text="Q",
        error=None,
        loading=False,
        session=ResearchSession(),
    )

    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.workflow.run_research_sync",
            return_value=done,
        ),
    ):
        _drain_on_submit(app_mod)

    assert st.loading is False
    assert st.error is None
    assert st.session.final_report == "# Hello"


def test_on_submit_exception_sets_error() -> None:
    from a2a_research.ui import app as app_mod

    st = SimpleNamespace(
        query_text="Q",
        error=None,
        loading=False,
        session=ResearchSession(),
    )

    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.workflow.run_research_sync",
            side_effect=RuntimeError("LLM down"),
        ),
    ):
        _drain_on_submit(app_mod)

    assert st.loading is False
    assert "LLM down" in (st.error or "")


def test_on_query_input_updates_state() -> None:
    from a2a_research.ui import app as app_mod

    st = SimpleNamespace(query_text="", session=ResearchSession(), loading=False, error=None)
    ev = SimpleNamespace(value="  hello ")
    with patch.object(app_mod.me, "state", return_value=st):
        app_mod._on_query_input(ev)
    assert st.query_text == "  hello "
