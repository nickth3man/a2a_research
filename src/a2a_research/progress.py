"""Progress events and queue helpers for real-time UI updates."""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import AsyncGenerator, Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from time import perf_counter
from typing import TYPE_CHECKING, Any, ClassVar

from a2a_research.app_logging import get_logger, log_event

if TYPE_CHECKING:
    from a2a_research.models import AgentRole

logger = get_logger(__name__)

__all__ = [
    "Bus",
    "PROMPT_DETAIL_MAX_CHARS",
    "ProgressEvent",
    "ProgressGranularity",
    "ProgressPhase",
    "ProgressQueue",
    "ProgressReporter",
    "create_progress_reporter",
    "current_session_id",
    "drain_progress_while_running",
    "emit",
    "emit_claim_verdict",
    "emit_handoff",
    "emit_llm_response",
    "emit_prompt",
    "emit_rate_limit",
    "emit_tool_call",
    "truncate_text",
    "using_session",
]

_session_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "a2a_research_session_id", default=""
)

PROMPT_DETAIL_MAX_CHARS = 4096


def current_session_id() -> str:
    """Return the session id set on the current async/thread context (empty if unset)."""
    return _session_var.get()


@contextmanager
def using_session(session_id: str) -> Iterator[None]:
    """Bind ``session_id`` to the current context for nested ``emit_*`` calls."""
    token = _session_var.set(session_id or "")
    try:
        yield
    finally:
        _session_var.reset(token)


def truncate_text(text: str, limit: int = PROMPT_DETAIL_MAX_CHARS) -> str:
    """Trim ``text`` to ``limit`` chars, appending a ``[truncated N chars]`` marker."""
    if text is None:
        return ""
    text = str(text)
    if len(text) <= limit:
        return text
    dropped = len(text) - limit
    return text[:limit] + f"\n…[truncated {dropped} chars]"


class ProgressGranularity(IntEnum):
    """User-selectable verbosity for progress updates."""

    AGENT = 1
    SUBSTEP = 2
    DETAIL = 3


class ProgressPhase(StrEnum):
    """Discrete workflow progress event phases."""

    STEP_STARTED = "step_started"
    STEP_SUBSTEP = "step_substep"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"


@dataclass(frozen=True)
class ProgressEvent:
    """Single progress update emitted by the workflow."""

    session_id: str
    phase: ProgressPhase
    role: AgentRole
    step_index: int
    total_steps: int
    substep_label: str
    substep_index: int = 0
    substep_total: int = 1
    granularity: ProgressGranularity = ProgressGranularity.AGENT
    detail: str = ""
    elapsed_ms: float | None = None
    created_at: float = field(default_factory=perf_counter)


ProgressQueue = asyncio.Queue[ProgressEvent | None]
ProgressReporter = Callable[[ProgressEvent | None], None]


class Bus:
    """In-process registry of per-session progress queues."""

    _queues: ClassVar[dict[str, ProgressQueue]] = {}
    _loops: ClassVar[dict[str, asyncio.AbstractEventLoop]] = {}

    @classmethod
    def register(cls, session_id: str, queue: ProgressQueue) -> None:
        cls._queues[session_id] = queue
        try:
            cls._loops[session_id] = asyncio.get_running_loop()
        except RuntimeError:
            pass

    @classmethod
    def get(cls, session_id: str) -> ProgressQueue | None:
        return cls._queues.get(session_id)

    @classmethod
    def get_loop(cls, session_id: str) -> asyncio.AbstractEventLoop | None:
        return cls._loops.get(session_id)

    @classmethod
    def unregister(cls, session_id: str) -> None:
        cls._queues.pop(session_id, None)
        cls._loops.pop(session_id, None)


_STEP_INDEX_BY_ROLE: dict[str, int] = {
    "planner": 0,
    "searcher": 1,
    "reader": 2,
    "fact_checker": 3,
    "synthesizer": 4,
}


def _step_index(role: AgentRole) -> int:
    return _STEP_INDEX_BY_ROLE.get(getattr(role, "value", str(role)), 0)


def _session_or_current(session_id: str | None) -> str:
    if session_id:
        return session_id
    return current_session_id()


def emit_prompt(
    role: AgentRole,
    label: str,
    prompt_text: str,
    *,
    system_text: str = "",
    session_id: str | None = None,
    model: str = "",
) -> None:
    """Emit a ``prompt_sent`` substep carrying (truncated) rendered prompt text."""
    sid = _session_or_current(session_id)
    full = (
        f"[SYSTEM]\n{system_text}\n\n[USER]\n{prompt_text}" if system_text else str(prompt_text)
    )
    summary = f"chars={len(full)}"
    if model:
        summary += f" model={model}"
    detail = f"{summary}\n{truncate_text(full)}"
    emit(sid, ProgressPhase.STEP_SUBSTEP, role, _step_index(role), 5, f"prompt_sent:{label}", detail=detail)


def emit_llm_response(
    role: AgentRole,
    label: str,
    response_text: str,
    *,
    elapsed_ms: float | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    finish_reason: str = "",
    model: str = "",
    session_id: str | None = None,
) -> None:
    """Emit an ``llm_response`` substep with latency, token counts, and (truncated) body."""
    sid = _session_or_current(session_id)
    bits: list[str] = [f"chars={len(response_text or '')}"]
    if model:
        bits.append(f"model={model}")
    if prompt_tokens is not None or completion_tokens is not None:
        bits.append(f"tokens={prompt_tokens or 0}/{completion_tokens or 0}")
    if finish_reason:
        bits.append(f"finish={finish_reason}")
    detail = " ".join(bits) + "\n" + truncate_text(response_text or "")
    emit(
        sid,
        ProgressPhase.STEP_SUBSTEP,
        role,
        _step_index(role),
        5,
        f"llm_response:{label}",
        detail=detail,
        elapsed_ms=elapsed_ms,
    )


def emit_handoff(
    *,
    direction: str,
    role: AgentRole,
    peer_role: AgentRole | str,
    payload_keys: list[str] | None = None,
    payload_bytes: int | None = None,
    payload_preview: str = "",
    session_id: str | None = None,
) -> None:
    """Emit a ``handoff_sent``/``handoff_received`` substep on the ``role`` panel."""
    sid = _session_or_current(session_id)
    peer = getattr(peer_role, "value", str(peer_role))
    bits: list[str] = [f"peer={peer}"]
    if payload_keys is not None:
        bits.append(f"keys=[{','.join(payload_keys)}]")
    if payload_bytes is not None:
        bits.append(f"bytes={payload_bytes}")
    detail = " ".join(bits)
    if payload_preview:
        detail += "\n" + truncate_text(payload_preview)
    label = "handoff_sent" if direction == "sent" else "handoff_received"
    emit(sid, ProgressPhase.STEP_SUBSTEP, role, _step_index(role), 5, label, detail=detail)


def emit_claim_verdict(
    role: AgentRole,
    claim_id: str,
    claim_text: str,
    old_verdict: str,
    new_verdict: str,
    *,
    confidence: float | None = None,
    source_count: int | None = None,
    session_id: str | None = None,
) -> None:
    """Emit a ``claim_verdict`` substep describing a single claim's transition."""
    sid = _session_or_current(session_id)
    bits = [f"id={claim_id}", f"{old_verdict}→{new_verdict}"]
    if confidence is not None:
        bits.append(f"conf={confidence:.2f}")
    if source_count is not None:
        bits.append(f"sources={source_count}")
    detail = " ".join(bits) + "\n" + truncate_text(claim_text, 400)
    emit(sid, ProgressPhase.STEP_SUBSTEP, role, _step_index(role), 5, "claim_verdict", detail=detail)


def emit_tool_call(
    role: AgentRole,
    tool_name: str,
    *,
    args_preview: str = "",
    result_preview: str = "",
    status: str = "",
    session_id: str | None = None,
) -> None:
    """Emit a ``tool_call`` substep for smolagents ReAct step visibility."""
    sid = _session_or_current(session_id)
    bits = [f"tool={tool_name}"]
    if status:
        bits.append(f"status={status}")
    parts = [" ".join(bits)]
    if args_preview:
        parts.append("args: " + truncate_text(args_preview, 300))
    if result_preview:
        parts.append("result: " + truncate_text(result_preview, 400))
    emit(
        sid,
        ProgressPhase.STEP_SUBSTEP,
        role,
        _step_index(role),
        5,
        "tool_call",
        detail="\n".join(parts),
    )


def emit_rate_limit(
    role: AgentRole,
    *,
    provider: str,
    attempt: int,
    max_attempts: int,
    delay_sec: float,
    reason: str = "",
    session_id: str | None = None,
) -> None:
    """Emit a ``rate_limit`` substep (amber warning) for throttles and retries."""
    sid = _session_or_current(session_id)
    bits = [
        f"provider={provider}",
        f"attempt={attempt}/{max_attempts}",
        f"retry_in={delay_sec:.2f}s",
    ]
    if reason:
        bits.append(f"reason={reason}")
    emit(
        sid,
        ProgressPhase.STEP_SUBSTEP,
        role,
        _step_index(role),
        5,
        "rate_limit",
        detail=" ".join(bits),
    )


def emit(
    session_id: str,
    phase: ProgressPhase,
    role: AgentRole,
    step_index: int,
    total_steps: int,
    substep_label: str,
    **extra: Any,
) -> None:
    """Emit a progress event to the registered queue for ``session_id``."""
    if not session_id:
        return
    queue = Bus.get(session_id)
    if queue is None:
        return
    granularity = extra.get("granularity")
    if not isinstance(granularity, ProgressGranularity):
        granularity = (
            ProgressGranularity.SUBSTEP
            if phase == ProgressPhase.STEP_SUBSTEP
            else ProgressGranularity.AGENT
        )
    event = ProgressEvent(
        session_id=session_id,
        phase=phase,
        role=role,
        step_index=step_index,
        total_steps=total_steps,
        substep_label=substep_label,
        substep_index=int(extra.get("substep_index") or 0),
        substep_total=int(extra.get("substep_total") or 1),
        granularity=granularity,
        detail=str(extra.get("detail") or ""),
        elapsed_ms=extra.get("elapsed_ms"),
    )
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    target_loop = Bus.get_loop(session_id)
    if running is None and target_loop is not None:
        try:
            target_loop.call_soon_threadsafe(queue.put_nowait, event)
        except RuntimeError:
            pass
        return
    queue.put_nowait(event)


def create_progress_reporter(
    loop: asyncio.AbstractEventLoop,
    queue: ProgressQueue,
) -> ProgressReporter:
    """Create a thread-safe reporter for worker-thread agent execution."""
    log_event(logger, 20, "progress.reporter.created", loop_id=id(loop), queue_id=id(queue))

    def report(event: ProgressEvent | None) -> None:
        log_event(
            logger,
            20,
            "progress.reporter.emit",
            queue_id=id(queue),
            progress=None
            if event is None
            else {
                "phase": event.phase,
                "session_id": event.session_id,
                "role": event.role,
                "step_index": event.step_index,
                "total_steps": event.total_steps,
                "substep_label": event.substep_label,
                "substep_index": event.substep_index,
                "substep_total": event.substep_total,
                "detail": event.detail,
                "elapsed_ms": event.elapsed_ms,
            },
        )
        loop.call_soon_threadsafe(queue.put_nowait, event)

    return report


async def drain_progress_while_running(
    queue: ProgressQueue,
    workflow_task: asyncio.Task[Any],
) -> AsyncGenerator[ProgressEvent, None]:
    """Yield queued events until the workflow finishes and the queue is drained."""
    log_event(
        logger,
        20,
        "progress.drain.start",
        queue_id=id(queue),
        workflow_task_id=id(workflow_task),
    )

    while True:
        queue_task = asyncio.create_task(queue.get())
        done, pending = await asyncio.wait(
            {queue_task, workflow_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if workflow_task in done and queue_task in pending:
            queue_task.cancel()
            await asyncio.gather(queue_task, return_exceptions=True)

        if queue_task in done:
            event = queue_task.result()
            if event is None:
                log_event(logger, 20, "progress.drain.stop.sentinel", queue_id=id(queue))
                break
            log_event(
                logger,
                20,
                "progress.drain.yield",
                queue_id=id(queue),
                phase=event.phase,
                role=event.role,
                step_index=event.step_index,
                substep_index=event.substep_index,
            )
            yield event

        if workflow_task in done:
            log_event(
                logger,
                20,
                "progress.drain.workflow_done",
                queue_id=id(queue),
                workflow_task_id=id(workflow_task),
            )
            try:
                workflow_task.result()
            except asyncio.CancelledError:
                log_event(
                    logger,
                    20,
                    "progress.drain.workflow_cancelled",
                    queue_id=id(queue),
                    workflow_task_id=id(workflow_task),
                )
                return
            while True:
                try:
                    event = queue.get_nowait()
                except asyncio.QueueEmpty:
                    log_event(logger, 20, "progress.drain.queue_empty", queue_id=id(queue))
                    break
                if event is None:
                    log_event(
                        logger, 20, "progress.drain.stop.trailing_sentinel", queue_id=id(queue)
                    )
                    return
                log_event(
                    logger,
                    20,
                    "progress.drain.trailing_yield",
                    queue_id=id(queue),
                    phase=event.phase,
                    role=event.role,
                    step_index=event.step_index,
                    substep_index=event.substep_index,
                )
                yield event
            return
