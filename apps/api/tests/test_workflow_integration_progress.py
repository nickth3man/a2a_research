"""End-to-end workflow progress/queue test over in-memory HTTP A2A services."""

from __future__ import annotations

import asyncio

import pytest

from core import AgentRole
from core.progress import (
    ProgressEvent,
    ProgressPhase,
    drain_progress_while_running,
)
from tests.workflow_integration_fixtures import (
    _configure_success_path,
)
from tests.workflow_integration_helpers import (
    _install_http_services,
)
from workflow import run_research_async


@pytest.mark.asyncio
async def test_progress_events_emitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_success_path(monkeypatch)
    shared_client = _install_http_services(monkeypatch)

    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()

    task = asyncio.create_task(
        run_research_async("When did JWST launch?", queue)
    )
    events = [e async for e in drain_progress_while_running(queue, task)]

    session = await task
    assert session.error is None

    phases = [e.phase for e in events]
    assert ProgressPhase.STEP_STARTED in phases
    assert any(e.role == AgentRole.PLANNER for e in events), (
        "Planner event missing"
    )
    assert any(e.role == AgentRole.SEARCHER for e in events), (
        "Searcher event missing"
    )
    assert any(e.role == AgentRole.READER for e in events), (
        "Reader event missing"
    )
    assert any(e.role == AgentRole.FACT_CHECKER for e in events), (
        "FactChecker event missing"
    )
    assert any(e.role == AgentRole.SYNTHESIZER for e in events), (
        "Synthesizer event missing"
    )
    assert any(e.phase == ProgressPhase.STEP_COMPLETED for e in events), (
        "Workflow completed event missing"
    )
    await shared_client.aclose()
