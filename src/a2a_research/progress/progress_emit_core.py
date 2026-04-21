"""Progress emit functions - Core emit and tools/rate limits."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from .progress_bus import Bus
from .progress_types import (
    ProgressEvent,
    ProgressGranularity,
    ProgressPhase,
    current_session_id,
)

if TYPE_CHECKING:
    from a2a_research.models import AgentRole

__all__ = ["emit", "emit_tool_call", "emit_rate_limit"]

_STEP_INDEX_BY_ROLE: dict[str, int] = {
    "preprocessor": 0,
    "clarifier": 1,
    "planner": 2,
    "searcher": 3,
    "ranker": 4,
    "reader": 5,
    "evidence_deduplicator": 6,
    "fact_checker": 7,
    "adversary": 8,
    "synthesizer": 9,
    "critic": 10,
    "postprocessor": 11,
}


def _step_index(role: "AgentRole") -> int:
    return _STEP_INDEX_BY_ROLE.get(getattr(role, "value", str(role)), 0)


def _session_or_current(session_id: str | None) -> str:
    return session_id or current_session_id()


def emit_tool_call(
    role: "AgentRole",
    tool_name: str,
    *,
    args_preview: str = "",
    result_preview: str = "",
    status: str = "",
    session_id: str | None = None,
) -> None:
    """Emit ``tool_call`` substep for ReAct step visibility."""
    sid = _session_or_current(session_id)
    bits = [f"tool={tool_name}"]
    if status:
        bits.append(f"status={status}")
    parts = [" ".join(bits)]
    if args_preview:
        parts.append("args: " + _truncate_text(args_preview, 300))
    if result_preview:
        parts.append("result: " + _truncate_text(result_preview, 400))
    emit(
        sid,
        ProgressPhase.STEP_SUBSTEP,
        role,
        _step_index(role),
        12,
        "tool_call",
        detail="\n".join(parts),
    )


def emit_rate_limit(
    role: "AgentRole",
    *,
    provider: str,
    attempt: int,
    max_attempts: int,
    delay_sec: float,
    reason: str = "",
    session_id: str | None = None,
) -> None:
    """Emit ``rate_limit`` substep for throttles and retries."""
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
        12,
        "rate_limit",
        detail=" ".join(bits),
    )


def emit(
    session_id: str,
    phase: ProgressPhase,
    role: "AgentRole",
    step_index: int,
    total_steps: int,
    substep_label: str,
    **extra: Any,
) -> None:
    """Emit a progress event to the registered queue."""
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
        with suppress(RuntimeError):
            target_loop.call_soon_threadsafe(queue.put_nowait, event)
        return
    queue.put_nowait(event)


def _truncate_text(text: str | None, limit: int) -> str:
    """Trim text to limit chars, appending truncation markers."""
    from .progress_types import PROMPT_DETAIL_MAX_CHARS
    from .progress_types import truncate_text as _tt

    if limit <= PROMPT_DETAIL_MAX_CHARS:
        if text is None:
            return ""
        if len(text) <= limit:
            return text
        dropped = len(text) - limit
        return text[:limit] + f" …[truncated {dropped} chars]"
    return _tt(text, limit)
