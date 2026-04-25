"""Status, event emission, and progress helpers."""

from __future__ import annotations

from core import ProgressPhase, emit
from core.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)
from core.models.errors import (
    ErrorEnvelope,
    ErrorSeverity,
)
from workflow.definitions import (
    STEP_INDEX,
    TOTAL_STEPS,
)

__all__ = ["emit_envelope", "emit_step", "mark_running_failed", "set_status"]

_SEVERITY_TO_PHASE: dict[ErrorSeverity, ProgressPhase] = {
    ErrorSeverity.FATAL: ProgressPhase.FINAL_DIAGNOSTICS,
    ErrorSeverity.WARNING: ProgressPhase.WARNING,
    ErrorSeverity.DEGRADED: ProgressPhase.DEGRADED_MODE,
}


def set_status(
    session: ResearchSession,
    role: AgentRole,
    status: AgentStatus,
    message: str,
) -> None:
    session.agent_results[role] = AgentResult(
        role=role, status=status, message=message
    )


def emit_step(
    session_id: str,
    role: AgentRole | None,
    phase: ProgressPhase,
    label: str,
    detail: str = "",
    envelope: ErrorEnvelope | None = None,
) -> None:
    step_index = STEP_INDEX.get(role, TOTAL_STEPS) if role else TOTAL_STEPS
    emit(
        session_id,
        phase,
        role,
        step_index,
        TOTAL_STEPS,
        label,
        detail=detail,
        envelope=envelope,
    )


def emit_envelope(
    session_id: str,
    envelope: ErrorEnvelope,
    session: ResearchSession,
) -> None:
    """Append envelope to error ledger and emit the matching SSE phase."""
    session.error_ledger.append(envelope)
    phase = _SEVERITY_TO_PHASE.get(envelope.severity, ProgressPhase.WARNING)
    emit_step(
        session_id,
        envelope.role,
        phase,
        envelope.code.value,
        detail=envelope.root_cause,
        envelope=envelope,
    )


def mark_running_failed(session: ResearchSession) -> None:
    for role, result in list(session.agent_results.items()):
        if result.status == AgentStatus.RUNNING:
            session.agent_results[role] = result.model_copy(
                update={"status": AgentStatus.FAILED, "message": "Aborted."}
            )
