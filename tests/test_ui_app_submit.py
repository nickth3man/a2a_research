"""Tests for Mesop app on_submit handler (mocked Mesop)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from a2a_research.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)

from tests.ui_app_helpers import _drain_on_submit, _make_state


async def test_on_submit_empty_query_sets_error() -> None:
    from a2a_research.ui import app as app_mod

    st = _make_state(query_text="   ")
    with patch.object(app_mod.me, "state", return_value=st):
        await _drain_on_submit(app_mod)
    assert st.session.error is not None
    assert "query" in st.session.error.lower()


async def test_on_submit_success_updates_session() -> None:
    from a2a_research.ui import app as app_mod

    done = ResearchSession(
        query="Q",
        agent_results={
            AgentRole.SYNTHESIZER: AgentResult(
                role=AgentRole.SYNTHESIZER,
                status=AgentStatus.COMPLETED,
            ),
        },
        final_report="# Hello",
    )
    st = _make_state(query_text="Q")

    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.workflow.run_research_async",
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

    st = _make_state(query_text="Q")

    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.workflow.run_research_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM down"),
        ),
    ):
        await _drain_on_submit(app_mod)

    assert st.loading is False
    assert "LLM down" in (st.session.error or "")


async def test_on_submit_cancelled_sets_recoverable_error() -> None:
    from a2a_research.ui import app as app_mod

    st = _make_state(query_text="Q")

    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.workflow.run_research_async",
            new_callable=AsyncMock,
            side_effect=asyncio.CancelledError(),
        ),
    ):
        await _drain_on_submit(app_mod)

    assert st.loading is False
    assert st.progress_pct == 0.0
    assert (
        st.session.error == "Live update stream was interrupted. Please retry."
    )


async def test_on_submit_success_yields_twice() -> None:
    """Loading flush + final UI flush."""
    from a2a_research.ui import app as app_mod

    done = ResearchSession(query="Q", final_report="x")
    st = _make_state(query_text="Q")
    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.workflow.run_research_async",
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

    st = _make_state(
        query_text="Q", loading=True, session=ResearchSession(query="Q")
    )
    mock_async = AsyncMock()
    with (
        patch.object(app_mod.me, "state", return_value=st),
        patch(
            "a2a_research.workflow.run_research_async",
            new_callable=AsyncMock,
            side_effect=mock_async,
        ),
    ):
        await _drain_on_submit(app_mod)
    mock_async.assert_not_called()
