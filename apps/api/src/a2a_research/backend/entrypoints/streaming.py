"""SSE streaming helpers for the FastAPI research gateway."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from a2a_research.backend.core.progress.progress_utils import (
    drain_progress_while_running,
)
from a2a_research.backend.entrypoints.api_serializers import (
    PHASE_TO_EVENT,
    serialize_progress,
    serialize_result,
    sse,
)
from a2a_research.backend.entrypoints.session_manager import (
    get_session_task,
    unregister_session,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


async def stream_events(
    session_id: str,
) -> AsyncGenerator[str, None]:
    """Stream SSE events for a research session."""
    task = get_session_task(session_id)
    from a2a_research.backend.core.progress import Bus

    queue = Bus.get(session_id)

    if task is None or queue is None:
        yield sse(
            "app-error",
            {
                "type": "error",
                "session_id": session_id,
                "message": "Session not found",
            },
        )
        return

    completed = False
    try:
        async for event in drain_progress_while_running(queue, task):
            phase = str(event.phase) if event.phase else ""
            sse_event = PHASE_TO_EVENT.get(phase, "progress")
            yield sse(sse_event, serialize_progress(event))

        try:
            session = await task
        except Exception as exc:
            yield sse(
                "app-error",
                {
                    "type": "error",
                    "session_id": session_id,
                    "message": str(exc),
                },
            )
            unregister_session(session_id)
            return

        if session.error:
            yield sse(
                "app-error",
                {
                    "type": "error",
                    "session_id": session_id,
                    "message": session.error,
                },
            )

        yield sse("result", serialize_result(session))
        unregister_session(session_id)
        completed = True
    except asyncio.CancelledError:
        if not task.done():
            task.cancel()
        unregister_session(session_id)
        raise
    finally:
        if completed or get_session_task(session_id) is None:
            Bus.unregister(session_id)
