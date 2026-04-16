"""Tests for Mesop app handlers (mocked Mesop)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

from a2a_research.models import AgentResult, AgentRole, AgentStatus, ResearchSession

if TYPE_CHECKING:
    from mesop.events import InputEvent


async def _drain_on_submit(app_mod, mock_event: MagicMock | None = None) -> None:
    agen = app_mod._on_submit(mock_event or MagicMock())
    async for _ in agen:
        pass


async def test_on_submit_empty_query_sets_error() -> None:
    from a2a_research.ui import app as app_mod

    st = SimpleNamespace(
        query_text="   ",
        loading=False,
        session=ResearchSession(),
        progress_granularity=1,
        current_substep="",
        progress_pct=0.0,
        progress_step_label="",
        progress_running_substeps=[],
    )
    with patch.object(app_mod.me, "state", return_value=st):
        await _drain_on_submit(app_mod)
    assert st.session.error is not None
    assert "query" in st.session.error.lower()


async def test_on_submit_success_updates_session() -> None:
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
        loading=False,
        session=ResearchSession(),
        progress_granularity=1,
        current_substep="",
        progress_pct=0.0,
        progress_step_label="",
        progress_running_substeps=[],
    )

    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.agents.pocketflow.run_workflow_async",
            new_callable=AsyncMock,
            return_value=done,
        ),
    ):
        await _drain_on_submit(app_mod)

    assert st.loading is False
    assert st.session.error is None
    assert st.session.final_report == "# Hello"


async def test_on_submit_exception_sets_error() -> None:
    from a2a_research.ui import app as app_mod

    st = SimpleNamespace(
        query_text="Q",
        loading=False,
        session=ResearchSession(),
        progress_granularity=1,
        current_substep="",
        progress_pct=0.0,
        progress_step_label="",
        progress_running_substeps=[],
    )

    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.agents.pocketflow.run_workflow_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM down"),
        ),
    ):
        await _drain_on_submit(app_mod)

    assert st.loading is False
    assert "LLM down" in (st.session.error or "")


async def test_on_submit_cancelled_sets_recoverable_error() -> None:
    from a2a_research.ui import app as app_mod

    st = SimpleNamespace(
        query_text="Q",
        loading=False,
        session=ResearchSession(),
        progress_granularity=1,
        current_substep="",
        progress_pct=0.0,
        progress_step_label="",
        progress_running_substeps=[],
    )

    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.agents.pocketflow.run_workflow_async",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError(),
        ),
    ):
        await _drain_on_submit(app_mod)

    assert st.loading is False
    assert st.progress_pct == 0.0
    assert st.session.error == "Live update stream was interrupted. Please retry."


async def test_on_submit_success_yields_twice() -> None:
    """Loading flush + final UI flush."""
    from a2a_research.ui import app as app_mod

    done = ResearchSession(query="Q", final_report="x")
    st = SimpleNamespace(
        query_text="Q",
        loading=False,
        session=ResearchSession(),
        progress_granularity=1,
        current_substep="",
        progress_pct=0.0,
        progress_step_label="",
        progress_running_substeps=[],
    )
    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.agents.pocketflow.run_workflow_async",
            new_callable=AsyncMock,
            return_value=done,
        ),
    ):
        agen = app_mod._on_submit(MagicMock())
        yields = 0
        async for _ in agen:
            yields += 1
    assert yields >= 2


async def test_on_submit_skips_when_already_loading() -> None:
    from a2a_research.ui import app as app_mod

    st = SimpleNamespace(
        query_text="Q",
        loading=True,
        session=ResearchSession(query="Q"),
        progress_granularity=1,
        current_substep="",
        progress_pct=0.0,
        progress_step_label="",
        progress_running_substeps=[],
    )
    mock_async = AsyncMock()
    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.agents.pocketflow.run_workflow_async",
            new_callable=AsyncMock,
            side_effect=mock_async,
        ),
    ):
        await _drain_on_submit(app_mod)
    mock_async.assert_not_called()


def test_on_query_input_updates_state() -> None:
    from a2a_research.ui import app as app_mod

    st = SimpleNamespace(
        query_text="",
        session=ResearchSession(),
        loading=False,
        progress_granularity=1,
        current_substep="",
        progress_pct=0.0,
        progress_step_label="",
        progress_running_substeps=[],
    )
    ev = cast("InputEvent", SimpleNamespace(value="  hello "))
    with patch.object(app_mod.me, "state", return_value=st):
        app_mod._on_query_input(ev)
    assert st.query_text == "  hello "
