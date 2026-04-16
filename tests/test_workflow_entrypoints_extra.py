"""Extra entrypoint coverage (exceptions and coordinator wrapper)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from a2a_research.models import AgentRole, ResearchSession


@pytest.mark.asyncio
async def test_run_workflow_reraises_after_flow_failure() -> None:
    shared: dict = {}
    mock_flow = MagicMock()
    mock_flow.run_async = AsyncMock(side_effect=RuntimeError("flow failed"))

    with patch(
        "a2a_research.workflow.entrypoints.get_workflow",
        return_value=(mock_flow, shared),
    ):
        from a2a_research.workflow.entrypoints import run_workflow

        with pytest.raises(RuntimeError, match="flow failed"):
            await run_workflow("why")


@pytest.mark.asyncio
async def test_run_workflow_from_session_delegates() -> None:
    out = ResearchSession(query="done")
    with patch(
        "a2a_research.workflow.entrypoints.run_coordinator",
        new_callable=AsyncMock,
        return_value=out,
    ) as rc:
        from a2a_research.workflow.entrypoints import run_workflow_from_session

        s = ResearchSession(query="start")
        result = await run_workflow_from_session(s)
    rc.assert_awaited_once_with(s)
    assert result is out


def test_get_workflow_for_roles_imports_builder() -> None:
    with patch("a2a_research.workflow.builder.build_workflow") as bw:
        bw.return_value = (MagicMock(), {})
        from a2a_research.workflow.entrypoints import get_workflow_for_roles

        get_workflow_for_roles([AgentRole.RESEARCHER])
    bw.assert_called_once_with([AgentRole.RESEARCHER])


def test_run_workflow_sync_runs_coroutine() -> None:
    session = ResearchSession(query="sync")

    async def fake_workflow(_q: str, _roles: list | None = None) -> ResearchSession:
        return session

    with patch("a2a_research.workflow.entrypoints.run_workflow", fake_workflow):
        from a2a_research.workflow.entrypoints import run_workflow_sync

        out = run_workflow_sync("sync")
    assert out is session


@pytest.mark.asyncio
async def test_run_workflow_async_awaits_run_workflow() -> None:
    session = ResearchSession(query="async")
    with patch(
        "a2a_research.workflow.entrypoints.run_workflow",
        new_callable=AsyncMock,
        return_value=session,
    ) as rw:
        from a2a_research.workflow.entrypoints import run_workflow_async

        out = await run_workflow_async("async", [AgentRole.RESEARCHER])
    rw.assert_awaited_once_with("async", [AgentRole.RESEARCHER])
    assert out is session
