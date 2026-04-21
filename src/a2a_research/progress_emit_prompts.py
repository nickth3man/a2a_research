"""Progress emit functions - Prompt and LLM response."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.progress_bus import Bus
from a2a_research.progress_types import (
    ProgressGranularity,
    ProgressPhase,
    current_session_id,
    truncate_text,
)

if TYPE_CHECKING:
    from a2a_research.models import AgentRole

__all__ = ["emit_prompt", "emit_llm_response"]

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


def emit_prompt(
    role: "AgentRole",
    label: str,
    prompt_text: str,
    *,
    system_text: str = "",
    session_id: str | None = None,
    model: str = "",
) -> None:
    """Emit ``prompt_sent`` substep with rendered prompt text."""
    sid = _session_or_current(session_id)
    full = (
        f"[SYSTEM]\n{system_text}\n\n[USER]\n{prompt_text}"
        if system_text
        else str(prompt_text)
    )
    summary = f"chars={len(full)}"
    if model:
        summary += f" model={model}"
    detail = f"{summary}\n{truncate_text(full)}"
    _emit(
        sid,
        ProgressPhase.STEP_SUBSTEP,
        role,
        _step_index(role),
        12,
        f"prompt_sent:{label}",
        detail=detail,
    )


def emit_llm_response(
    role: "AgentRole",
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
    """Emit ``llm_response`` substep with latency and tokens."""
    sid = _session_or_current(session_id)
    bits: list[str] = [f"chars={len(response_text or '')}"]
    if model:
        bits.append(f"model={model}")
    if prompt_tokens is not None or completion_tokens is not None:
        bits.append(f"tokens={prompt_tokens or 0}/{completion_tokens or 0}")
    if finish_reason:
        bits.append(f"finish={finish_reason}")
    detail = " ".join(bits) + "\n" + truncate_text(response_text or "")
    _emit(
        sid,
        ProgressPhase.STEP_SUBSTEP,
        role,
        _step_index(role),
        12,
        f"llm_response:{label}",
        detail=detail,
        elapsed_ms=elapsed_ms,
    )


def _emit(
    session_id: str,
    phase: ProgressPhase,
    role: "AgentRole",
    step_index: int,
    total_steps: int,
    substep_label: str,
    **extra,
) -> None:
    """Forward to the central emit function to avoid circular imports."""
    from a2a_research.progress_emit_core import emit

    emit(
        session_id,
        phase,
        role,
        step_index,
        total_steps,
        substep_label,
        **extra,
    )
