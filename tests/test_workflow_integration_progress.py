"""End-to-end workflow progress/queue test over in-memory HTTP A2A services."""

from __future__ import annotations

import asyncio

import pytest

from a2a_research.models import AgentRole
from a2a_research.progress import (
    ProgressEvent, ProgressPhase, drain_progress_while_running
)
from a2a_research.workflow import run_research_async

from tests.workflow_integration_helpers import (
    _configure_success_path,
    _install_http_services,
)


@pytest.mark.asyncio
async def test_progress_events_emitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_success_path(monkeypatch)
    shared_client = _install_http_services(monkeypatch)

    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    workflow_task = asyncio.create_task(
        run_research_async("When did JWST launch?", progress_queue=queue)
    )
    events = [
        event
        async for event in drain_progress_while_running(queue, workflow_task)
    ]
    session = await workflow_task

    assert session.error is None
    started_roles = {
        event.role
        for event in events
        if event.phase == ProgressPhase.STEP_STARTED
    }
    assert started_roles == {
        AgentRole.PLANNER,
        AgentRole.SEARCHER,
        AgentRole.READER,
        AgentRole.FACT_CHECKER,
        AgentRole.SYNTHESIZER,
    }
    assert any(
        event.substep_label == "verify"
        and event.phase == ProgressPhase.STEP_SUBSTEP
        for event in events
    )
    await shared_client.aclose()
