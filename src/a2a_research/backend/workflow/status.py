"""Status, event emission, and progress helpers."""

from __future__ import annotations

from a2a_research.backend.core.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)
from a2a_research.backend.core.progress import ProgressPhase, emit
from a2a_research.backend.workflow.definitions import (
    STEP_INDEX_V2,
    TOTAL_STEPS_V2,
)

__all__ = ["emit_v2", "mark_running_failed", "set_status"]


def set_status(
    session: ResearchSession,
    role: AgentRole,
    status: AgentStatus,
    message: str,
) -> None:
    session.agent_results[role] = AgentResult(
        role=role, status=status, message=message
    )


def emit_v2(
    session_id: str,
    role: AgentRole | None,
    phase: ProgressPhase,
    label: str,
    detail: str = "",
) -> None:
    step_index = STEP_INDEX_V2.get(role, 0) if role else 0
    emit(
        session_id,
        phase,
        role,
        step_index,
        TOTAL_STEPS_V2,
        label,
        detail=detail,
    )


def mark_running_failed(session: ResearchSession) -> None:
    for role, result in list(session.agent_results.items()):
        if result.status == AgentStatus.RUNNING:
            session.agent_results[role] = result.model_copy(
                update={"status": AgentStatus.FAILED, "message": "Aborted."}
            )
