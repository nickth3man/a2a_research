"""FastAPI SSE gateway for the React frontend."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.progress import Bus
from a2a_research.backend.core.progress.progress_utils import (
    drain_progress_while_running,
)
from a2a_research.backend.entrypoints.agent_mounts import mount_agents
from a2a_research.backend.entrypoints.api_serializers import (
    PHASE_TO_EVENT,
    serialize_progress,
    serialize_result,
    sse,
)
from a2a_research.backend.workflow.status import mark_running_failed

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from a2a_research.backend.core.models.session import ResearchSession

logger = get_logger(__name__)

app = FastAPI(title="A2A Research Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_sessions: dict[str, asyncio.Task[ResearchSession]] = {}


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    session_id: str


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/research", response_model=ResearchResponse)
async def start_research(req: ResearchRequest) -> ResearchResponse:
    from a2a_research.backend.core.models import ResearchSession
    from a2a_research.backend.workflow.definitions import STEP_INDEX

    session = ResearchSession(query=req.query)
    session.roles = list(STEP_INDEX.keys())
    session.ensure_agent_results()

    queue: asyncio.Queue[Any] = asyncio.Queue()
    Bus.register(session.id, queue)

    async def _run() -> ResearchSession:
        import a2a_research.backend.core.a2a as _a2a
        from a2a_research.backend.core.models import BudgetConsumption
        from a2a_research.backend.core.settings import settings
        from a2a_research.backend.workflow.definitions import (
            budget_from_settings,
        )
        from a2a_research.backend.workflow.engine import drive

        client = _a2a.A2AClient(_a2a.get_registry())
        session.budget_consumed = BudgetConsumption()
        try:
            try:
                await asyncio.wait_for(
                    drive(session, client, req.query, budget_from_settings()),
                    timeout=settings.workflow_timeout,
                )
            except TimeoutError:
                session.error = (
                    f"Workflow timed out after "
                    f"{settings.workflow_timeout:.0f}s"
                    " — partial results below."
                )
                mark_running_failed(session)
                logger.warning(
                    "api.workflow.timeout session_id=%s", session.id
                )
            except Exception as exc:
                session.error = str(exc)
                mark_running_failed(session)
                logger.exception(
                    "api.workflow.error session_id=%s", session.id
                )
            return session
        finally:
            queue.put_nowait(None)
            Bus.unregister(session.id)

    task = asyncio.create_task(_run())
    _sessions[session.id] = task

    return ResearchResponse(session_id=session.id)


async def _stream_events(
    session_id: str,
) -> AsyncGenerator[str, None]:
    task = _sessions.get(session_id)
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
            _sessions.pop(session_id, None)
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
        _sessions.pop(session_id, None)
    finally:
        Bus.unregister(session_id)


@app.get("/api/research/{session_id}/stream")
async def stream_research(session_id: str) -> StreamingResponse:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(
        _stream_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Agent sub-apps ──
mount_agents(app)
