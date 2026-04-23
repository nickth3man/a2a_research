"""FastAPI SSE gateway for the React frontend."""

from __future__ import annotations

import asyncio
import json
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
from a2a_research.backend.workflow.status import mark_running_failed
from a2a_research.backend.workflow.workflow_engine import run_workflow_async

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from a2a_research.backend.core.models.claims import Claim
    from a2a_research.backend.core.models.errors import ErrorEnvelope
    from a2a_research.backend.core.models.reports import WebSource
    from a2a_research.backend.core.models.session import ResearchSession
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

# SSE phases that map to non-progress event names
_PHASE_TO_EVENT: dict[str, str] = {
    "warning": "warning",
    "retrying": "retrying",
    "degraded_mode": "degraded_mode",
    "final_diagnostics": "final_diagnostics",
}


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


def _serialize_envelope(envelope: ErrorEnvelope) -> dict[str, Any]:
    return {
        "role": _normalize_role(str(envelope.role) if envelope.role else None),
        "code": envelope.code,
        "severity": envelope.severity,
        "retryable": envelope.retryable,
        "root_cause": envelope.root_cause,
        "remediation": envelope.remediation,
        "trace_id": envelope.trace_id,
    }


def _serialize_progress(event: ProgressEvent) -> dict[str, Any]:
    data: dict[str, Any] = {
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
    if event.envelope is not None:
        data["envelope"] = _serialize_envelope(event.envelope)
    return data


def _serialize_claim(claim: Claim) -> dict[str, Any]:
    return {
        "text": claim.text,
        "verdict": _normalize_verdict(str(claim.verdict)),
        "confidence": claim.confidence,
        "sources": list(claim.sources),
        "evidence": (
            claim.evidence_snippets[0] if claim.evidence_snippets else None
        ),
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
        "diagnostics": [
            _serialize_envelope(e) for e in session.error_ledger
        ],
        "error": session.error,
    }


async def _run_workflow(
    session_id: str,
    query: str,
    queue: asyncio.Queue[Any],
) -> ResearchSession:
    logger.info(
        "api.workflow.start session_id=%s query=%r", session_id, query
    )
    # run_workflow_async creates its own session; we need it to use the
    # already-registered queue. Register before calling so the engine
    # picks it up on Bus.get().
    session = await run_workflow_async(query, progress_queue=queue)
    logger.info(
        "api.workflow.done session_id=%s error=%s", session_id, session.error
    )
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
    # Pre-generate a placeholder session_id for the SSE route; the real
    # session id is assigned inside run_workflow_async. We use a queue
    # handshake: the queue is registered by run_workflow_async using its
    # internal session id, so we let it drive. We store the task keyed
    # by a temporary key and update after the session id is known.
    #
    # Simpler approach: create a dedicated queue here; run_workflow_async
    # accepts an optional progress_queue and registers it internally.
    # We expose the session_id from the ResearchSession returned by the task.
    # But the SSE client needs the session_id before the task finishes.
    #
    # Solution: create session id first here using ResearchSession, register
    # queue, then pass query + pre-created queue to engine.
    from a2a_research.backend.core.models import ResearchSession
    from a2a_research.backend.workflow.definitions import STEP_INDEX

    session = ResearchSession(query=req.query)
    session.roles = list(STEP_INDEX.keys())
    session.ensure_agent_results()

    queue: asyncio.Queue[Any] = asyncio.Queue()
    Bus.register(session.id, queue)

    # Run the workflow, passing the pre-registered queue so the engine
    # reuses it rather than creating a new one.
    async def _run() -> ResearchSession:
        from a2a_research.backend.core.models import BudgetConsumption
        import a2a_research.backend.core.a2a as _a2a
        from a2a_research.backend.core.settings import settings
        from a2a_research.backend.workflow.definitions import (
            budget_from_settings,
        )
        from a2a_research.backend.workflow.engine import drive

        client = _a2a.A2AClient(_a2a.get_registry())
        session.budget_consumed = BudgetConsumption()
        try:
            await asyncio.wait_for(
                drive(session, client, req.query, budget_from_settings()),
                timeout=settings.workflow_timeout,
            )
        except TimeoutError:
            from a2a_research.backend.core.settings import settings as s
            session.error = (
                f"Workflow timed out after {s.workflow_timeout:.0f}s"
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
        queue.put_nowait(None)
        Bus.unregister(session.id)
        return session

    task = asyncio.create_task(_run())
    _sessions[session.id] = task

    return ResearchResponse(session_id=session.id)


async def _stream_events(
    session_id: str,
) -> AsyncGenerator[str, None]:
    task = _sessions.get(session_id)
    queue = Bus.get(session_id)

    if task is None or queue is None:
        yield _sse(
            "app-error",
            {
                "type": "error",
                "session_id": session_id,
                "message": "Session not found",
            },
        )
        return

    async for event in drain_progress_while_running(queue, task):
        phase = str(event.phase) if event.phase else ""
        sse_event = _PHASE_TO_EVENT.get(phase, "progress")
        yield _sse(sse_event, _serialize_progress(event))

    try:
        session = await task
    except Exception as exc:
        yield _sse(
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
        yield _sse(
            "app-error",
            {
                "type": "error",
                "session_id": session_id,
                "message": session.error,
            },
        )

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


# ── Agent sub-apps ──
mount_agents(app)
