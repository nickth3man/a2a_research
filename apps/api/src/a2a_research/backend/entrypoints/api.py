"""FastAPI SSE gateway for the React frontend."""

from __future__ import annotations

import asyncio
import logfire
from time import monotonic
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.telemetry import configure_telemetry
from a2a_research.backend.core.progress import Bus
from a2a_research.backend.core.progress.progress_utils import (
    drain_progress_while_running,
)
from a2a_research.backend.core.settings import settings
from a2a_research.backend.entrypoints.agent_mounts import mount_agents
from a2a_research.backend.entrypoints.api_models import (
    ResearchRequest,
    ResearchResponse,
)
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

configure_telemetry()

app = FastAPI(title="A2A Research Gateway")

logfire.instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)

_sessions: dict[str, asyncio.Task[ResearchSession]] = {}
_session_created_at: dict[str, float] = {}


def _prune_expired_sessions() -> None:
    now = monotonic()
    expired = [
        session_id
        for session_id, created_at in _session_created_at.items()
        if now - created_at > settings.session_ttl_seconds
    ]
    for session_id in expired:
        task = _sessions.pop(session_id, None)
        _session_created_at.pop(session_id, None)
        Bus.unregister(session_id)
        if task is not None and not task.done():
            task.cancel()


def _running_session_count() -> int:
    _prune_expired_sessions()
    return sum(1 for task in _sessions.values() if not task.done())


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    api_key: str | None = Query(default=None),
) -> None:
    if not settings.api_key:
        return
    if x_api_key == settings.api_key or api_key == settings.api_key:
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/research", response_model=ResearchResponse)
async def start_research(
    req: ResearchRequest, _auth: None = Depends(require_api_key)
) -> ResearchResponse:
    from a2a_research.backend.core.models import ResearchSession
    from a2a_research.backend.workflow.definitions import STEP_INDEX

    if _running_session_count() >= settings.max_concurrent_sessions:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many concurrent research sessions",
        )

    query = req.query
    session = ResearchSession(query=query)
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
                    drive(session, client, query, budget_from_settings()),
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
    _session_created_at[session.id] = monotonic()

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
            _sessions.pop(session_id, None)
            _session_created_at.pop(session_id, None)
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
        _session_created_at.pop(session_id, None)
        completed = True
    except asyncio.CancelledError:
        if not task.done():
            task.cancel()
        _sessions.pop(session_id, None)
        _session_created_at.pop(session_id, None)
        raise
    finally:
        if completed or session_id not in _sessions:
            Bus.unregister(session_id)


@app.get("/api/research/{session_id}/stream")
async def stream_research(
    session_id: str, _auth: None = Depends(require_api_key)
) -> StreamingResponse:
    _prune_expired_sessions()
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


mount_agents(app)
