"""v2 workflow engine smoke tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from a2a_research.models import ResearchSession
from a2a_research.workflow import run_workflow_v2_async


@pytest.mark.asyncio
async def test_run_workflow_v2_async_returns_session() -> None:
    with patch(
        "a2a_research.workflow.workflow_engine.drive_v2",
        new_callable=AsyncMock,
    ) as mock_drive:
        session = await run_workflow_v2_async("test query")
        assert isinstance(session, ResearchSession)
        assert session.query == "test query"
        assert session.roles
        mock_drive.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_workflow_v2_async_sets_error_on_failure() -> None:
    with patch(
        "a2a_research.workflow.workflow_engine.drive_v2",
        new_callable=AsyncMock,
        side_effect=RuntimeError("agent failed"),
    ):
        session = await run_workflow_v2_async("test query")
        assert session.error == "agent failed"
