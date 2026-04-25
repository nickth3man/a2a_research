"""Tests for entrypoints.streaming SSE helpers."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import MagicMock, patch

import pytest

from core import (
    AgentRole,
    Bus,
    ProgressEvent,
    ProgressPhase,
    ResearchSession,
)


@pytest.mark.asyncio
async def test_stream_events_happy_path_yields_result() -> None:
    from entrypoints import streaming

    sid = f"st-{uuid.uuid4().hex[:8]}"
    q: asyncio.Queue[object] = asyncio.Queue()
    Bus.register(sid, q)
    pev = ProgressEvent(
        session_id=sid,
        phase=ProgressPhase.STEP_COMPLETED,
        role=AgentRole.PLANNER,
        step_index=0,
        total_steps=1,
        substep_label="x",
    )

    async def mock_drain(
        _queue: asyncio.Queue[object], _task: asyncio.Task[ResearchSession]
    ) -> object:
        yield pev

    async def return_session() -> ResearchSession:
        return ResearchSession(id=sid, query="q", final_report="rep")

    t = asyncio.create_task(return_session())
    with (
        patch(
            "entrypoints.streaming.drain_progress_while_running", mock_drain
        ),
        patch("entrypoints.streaming.get_session_task", return_value=t),
    ):
        chunks: list[str] = []
        async for line in streaming.stream_events(sid):
            chunks.append(line)
    text = "".join(chunks)
    assert "result" in text
    assert "rep" in text


@pytest.mark.asyncio
async def test_stream_events_resolves_error_from_failed_task() -> None:
    from entrypoints import streaming

    sid = f"e-{uuid.uuid4().hex[:8]}"
    q: asyncio.Queue[object] = asyncio.Queue()
    Bus.register(sid, q)
    try:

        async def no_events(
            _queue: asyncio.Queue[object], _task: asyncio.Task[ResearchSession]
        ) -> object:
            if False:  # pragma: no cover
                yield

        async def failing_task() -> ResearchSession:
            raise RuntimeError("workflow exploded")

        t = asyncio.create_task(failing_task())
        with (
            patch(
                "entrypoints.streaming.drain_progress_while_running", no_events
            ),
            patch("entrypoints.streaming.get_session_task", return_value=t),
        ):
            out = [x async for x in streaming.stream_events(sid)]
    finally:
        if Bus.get(sid) is not None:
            Bus.unregister(sid)
    text = "".join(out)
    assert "workflow exploded" in text
    assert "app-error" in text


@pytest.mark.asyncio
async def test_stream_events_emits_error_when_session_has_error() -> None:
    from entrypoints import streaming

    sid = f"err-{uuid.uuid4().hex[:8]}"
    q: asyncio.Queue[object] = asyncio.Queue()
    Bus.register(sid, q)
    try:

        async def one_progress(
            _queue: asyncio.Queue[object], _task: asyncio.Task[ResearchSession]
        ) -> object:
            yield ProgressEvent(
                session_id=sid,
                phase=ProgressPhase.STEP_SUBSTEP,
                role=AgentRole.PLANNER,
                step_index=0,
                total_steps=1,
                substep_label="p",
            )

        async def return_with_error() -> ResearchSession:
            return ResearchSession(id=sid, query="q", error="nope")

        t2 = asyncio.create_task(return_with_error())
        with (
            patch(
                "entrypoints.streaming.drain_progress_while_running",
                one_progress,
            ),
            patch("entrypoints.streaming.get_session_task", return_value=t2),
        ):
            out = [x async for x in streaming.stream_events(sid)]
    finally:
        if Bus.get(sid) is not None:
            Bus.unregister(sid)
    text = "".join(out)
    assert "nope" in text


@pytest.mark.asyncio
async def test_stream_events_yields_error_when_no_queue() -> None:
    from entrypoints import streaming

    t = MagicMock()
    t.done.return_value = True
    with patch.object(streaming, "get_session_task", return_value=t):
        with patch("core.Bus.get", return_value=None):
            chunks: list[str] = []
            async for line in streaming.stream_events("no-queue"):
                chunks.append(line)
    text = "".join(chunks)
    assert "Session not found" in text
    assert "app-error" in text
