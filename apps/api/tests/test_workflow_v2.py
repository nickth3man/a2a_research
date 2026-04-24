"""Workflow engine smoke tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from a2a_research.backend.core.models import ResearchSession
from a2a_research.backend.workflow import run_workflow_async


@pytest.mark.asyncio
async def test_run_workflow_async_returns_session() -> None:
    with patch(
        "a2a_research.backend.workflow.workflow_engine.drive",
        new_callable=AsyncMock,
    ) as mock_drive:
        session = await run_workflow_async("test query")
        assert isinstance(session, ResearchSession)
        assert session.query == "test query"
        assert session.roles
        mock_drive.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_workflow_async_sets_error_on_failure() -> None:
    with patch(
        "a2a_research.backend.workflow.workflow_engine.drive",
        new_callable=AsyncMock,
        side_effect=RuntimeError("agent failed"),
    ):
        session = await run_workflow_async("test query")
        assert session.error == "agent failed"
