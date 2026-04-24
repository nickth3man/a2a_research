"""FastAPI SSE gateway for the React frontend."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.progress import Bus
from a2a_research.backend.core.settings import settings
from a2a_research.backend.core.telemetry import configure_telemetry
from a2a_research.backend.entrypoints.agent_mounts import mount_agents
from a2a_research.backend.entrypoints.api_models import (
    ResearchRequest,
    ResearchResponse,
)
from a2a_research.backend.entrypoints.session_manager import (
    get_session_task,
    prune_expired_sessions,
    register_session,
    running_session_count,
)
from a2a_research.backend.entrypoints.streaming import stream_events
from a2a_research.backend.workflow.status import mark_running_failed

if TYPE_CHECKING:
    from a2a_research.backend.core.models.session import ResearchSession

configure_telemetry()
logger = get_logger(__name__)
app = FastAPI(title="A2A Research Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    api_key: str | None = Query(default=None),
) -> None:
    """Validate API key if configured."""
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
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/research", response_model=ResearchResponse)
async def start_research(
    req: ResearchRequest, _auth: None = Depends(require_api_key)
) -> ResearchResponse:
    """Start a new research session."""
    from a2a_research.backend.core.models import ResearchSession
    from a2a_research.backend.workflow.definitions import STEP_INDEX

    if running_session_count() >= settings.max_concurrent_sessions:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many concurrent research sessions",
        )

    session = ResearchSession(query=req.query)
    session.roles = list(STEP_INDEX.keys())
    session.ensure_agent_results()

    queue: asyncio.Queue[Any] = asyncio.Queue()
    Bus.register(session.id, queue)

    async def _run() -> ResearchSession:
        import a2a_research.backend.core.a2a as _a2a
        from a2a_research.backend.core.models import BudgetConsumption
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
    register_session(session.id, task)
    return ResearchResponse(session_id=session.id)


@app.get("/api/research/{session_id}/stream")
async def stream_research(
    session_id: str, _auth: None = Depends(require_api_key)
) -> StreamingResponse:
    """Stream research progress via SSE."""
    prune_expired_sessions()
    if get_session_task(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(
        stream_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


mount_agents(app)
