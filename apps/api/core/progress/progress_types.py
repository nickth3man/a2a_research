"""Progress types and constants."""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from time import perf_counter
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from core import AgentRole, ErrorEnvelope

__all__ = [
    "PROMPT_DETAIL_MAX_CHARS",
    "ProgressEvent",
    "ProgressGranularity",
    "ProgressPhase",
    "ProgressQueue",
    "ProgressReporter",
    "current_session_id",
    "truncate_text",
    "using_session",
]

_session_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "a2a_research_session_id", default=""
)

PROMPT_DETAIL_MAX_CHARS = 4096


def current_session_id() -> str:
    """Return session id from current async/thread context."""
    return _session_var.get()


@contextmanager
def using_session(session_id: str) -> Iterator[None]:
    """Bind ``session_id`` to the current context."""
    token = _session_var.set(session_id or "")
    try:
        yield
    finally:
        _session_var.reset(token)


def truncate_text(
    text: str | None, limit: int = PROMPT_DETAIL_MAX_CHARS
) -> str:
    """Trim ``text`` to ``limit`` chars, appending truncation markers."""
    if text is None:
        return ""
    text = str(text)
    lines = text.splitlines() or [text]
    clipped_lines: list[str] = []
    for line in lines:
        if len(line) <= limit:
            clipped_lines.append(line)
            continue
        dropped = len(line) - limit
        clipped_lines.append(line[:limit] + f" …[truncated {dropped} chars]")
    return "\n".join(clipped_lines)


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
    # Diagnostic event types (map to distinct SSE event names)
    WARNING = "warning"
    RETRYING = "retrying"
    DEGRADED_MODE = "degraded_mode"
    FINAL_DIAGNOSTICS = "final_diagnostics"


@dataclass(frozen=True)
class ProgressEvent:
    """Single progress update emitted by the workflow."""

    session_id: str
    phase: ProgressPhase
    role: AgentRole | None
    step_index: int
    total_steps: int
    substep_label: str
    substep_index: int = 0
    substep_total: int = 1
    granularity: ProgressGranularity = ProgressGranularity.AGENT
    detail: str = ""
    elapsed_ms: float | None = None
    created_at: float = field(default_factory=perf_counter)
    envelope: ErrorEnvelope | None = None


ProgressQueue: TypeAlias = asyncio.Queue[ProgressEvent | None]
ProgressReporter: TypeAlias = Callable[[ProgressEvent | None], None]
