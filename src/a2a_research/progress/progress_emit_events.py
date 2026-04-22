"""Progress emit functions - Handoffs and claims."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .progress_types import (
    ProgressPhase,
    current_session_id,
    truncate_text,
)

if TYPE_CHECKING:
    from a2a_research.models import AgentRole

__all__ = ["emit_claim_verdict", "emit_handoff"]

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


def _step_index(role: AgentRole) -> int:
    return _STEP_INDEX_BY_ROLE.get(getattr(role, "value", str(role)), 0)


def _session_or_current(session_id: str | None) -> str:
    return session_id or current_session_id()


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
    """Emit handoff substep on the ``role`` panel."""
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
    _emit(
        sid,
        ProgressPhase.STEP_SUBSTEP,
        role,
        _step_index(role),
        12,
        label,
        detail=detail,
    )


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
    """Emit ``claim_verdict`` substep for a claim's transition."""
    sid = _session_or_current(session_id)
    bits = [f"id={claim_id}", f"{old_verdict}→{new_verdict}"]
    if confidence is not None:
        bits.append(f"conf={confidence:.2f}")
    if source_count is not None:
        bits.append(f"sources={source_count}")
    detail = " ".join(bits) + "\n" + truncate_text(claim_text, 400)
    _emit(
        sid,
        ProgressPhase.STEP_SUBSTEP,
        role,
        _step_index(role),
        12,
        "claim_verdict",
        detail=detail,
    )


def _emit(
    session_id: str,
    phase: ProgressPhase,
    role: AgentRole,
    step_index: int,
    total_steps: int,
    substep_label: str,
    **extra: Any,
) -> None:
    """Forward to the central emit function to avoid circular imports."""
    from .progress_emit_core import emit

    emit(
        session_id,
        phase,
        role,
        step_index,
        total_steps,
        substep_label,
        **extra,
    )
