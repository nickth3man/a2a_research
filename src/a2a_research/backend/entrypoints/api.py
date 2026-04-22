"""FastAPI SSE gateway for the React frontend.

POST /api/research          → {"session_id": str}
GET  /api/research/{id}/stream → SSE text/event-stream
GET  /api/health            → {"status": "ok"}
"""

from __future__ import annotations

import asyncio
import json
from time import perf_counter
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from a2a_research.backend.core.a2a import A2AClient, get_registry
from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.models import ResearchSession
from a2a_research.backend.core.progress import Bus
from a2a_research.backend.core.progress.progress_utils import (
    drain_progress_while_running,
)
from a2a_research.backend.core.settings import settings
from a2a_research.backend.workflow.coordinator_drive import drive
from a2a_research.backend.workflow.coordinator_helpers import (
    mark_running_failed,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from a2a_research.backend.core.models.claims import Claim
    from a2a_research.backend.core.models.reports import WebSource
    from a2a_research.backend.core.progress.progress_types import ProgressEvent

logger = get_logger(__name__)

app = FastAPI(title="A2A Research Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_sessions: dict[str, asyncio.Task[ResearchSession]] = {}

_ROLE_NORM: dict[str, str] = {"evidence_deduplicator": "deduplicator"}


def _normalize_role(role: str | None) -> str | None:
    if role is None:
        return None
    return _ROLE_NORM.get(role, role)


def _normalize_verdict(verdict: str) -> str:
    if verdict in ("SUPPORTED", "REFUTED"):
        return verdict
    return "UNVERIFIABLE"


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _serialize_progress(event: ProgressEvent) -> dict[str, Any]:
    return {
        "type": "progress",
        "session_id": event.session_id,
        "phase": event.phase,
        "role": _normalize_role(str(event.role) if event.role else None),
        "step_index": event.step_index,
        "total_steps": event.total_steps,
        "substep_label": event.substep_label,
        "substep_index": event.substep_index,
        "substep_total": event.substep_total,
        "detail": event.detail,
        "elapsed_ms": event.elapsed_ms,
    }


def _serialize_claim(claim: Claim) -> dict[str, Any]:
    return {
        "text": claim.text,
        "verdict": _normalize_verdict(str(claim.verdict)),
        "confidence": claim.confidence,
        "sources": list(claim.sources),
        "evidence": claim.evidence_snippets[0] if claim.evidence_snippets else None,
    }


def _serialize_source(source: WebSource) -> dict[str, str]:
    return {"url": source.url, "title": source.title}


def _serialize_result(session: ResearchSession) -> dict[str, Any]:
    return {
        "type": "result",
        "session_id": session.id,
        "report": session.final_report,
        "sources": [_serialize_source(s) for s in session.sources],
        "claims": [_serialize_claim(c) for c in session.claims],
        "error": session.error,
    }


async def _run_workflow(session: ResearchSession, queue: asyncio.Queue[Any]) -> ResearchSession:
    client = A2AClient(get_registry())
    started = perf_counter()
    logger.info("api.workflow.start session_id=%s query=%r", session.id, session.query)
    try:
        await asyncio.wait_for(
            drive(session, client, session.query),
            timeout=settings.workflow_timeout,
        )
    except TimeoutError:
        session.error = (
            f"Workflow timed out after {settings.workflow_timeout:.0f}s"
            " — partial results below."
        )
        mark_running_failed(session)
        logger.warning("api.workflow.timeout session_id=%s", session.id)
    except Exception as exc:
        session.error = str(exc)
        mark_running_failed(session)
        logger.exception("api.workflow.error session_id=%s", session.id)

    elapsed_ms = (perf_counter() - started) * 1000
    logger.info(
        "api.workflow.done session_id=%s elapsed_ms=%.1f error=%s",
        session.id,
        elapsed_ms,
        session.error,
    )
    queue.put_nowait(None)
    Bus.unregister(session.id)
    return session


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    session_id: str


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/research", response_model=ResearchResponse)
async def start_research(req: ResearchRequest) -> ResearchResponse:
    session = ResearchSession(query=req.query)
    session.ensure_agent_results()

    queue: asyncio.Queue[Any] = asyncio.Queue()
    Bus.register(session.id, queue)

    task = asyncio.create_task(_run_workflow(session, queue))
    _sessions[session.id] = task

    return ResearchResponse(session_id=session.id)


async def _stream_events(session_id: str) -> AsyncGenerator[str, None]:
    task = _sessions.get(session_id)
    queue = Bus.get(session_id)

    if task is None or queue is None:
        yield _sse("error", {"type": "error", "session_id": session_id, "message": "Session not found"})
        return

    async for event in drain_progress_while_running(queue, task):
        yield _sse("progress", _serialize_progress(event))

    try:
        session = await task
    except Exception as exc:
        yield _sse("error", {"type": "error", "session_id": session_id, "message": str(exc)})
        _sessions.pop(session_id, None)
        return

    if session.error:
        yield _sse("error", {"type": "error", "session_id": session_id, "message": session.error})

    yield _sse("result", _serialize_result(session))
    _sessions.pop(session_id, None)


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
