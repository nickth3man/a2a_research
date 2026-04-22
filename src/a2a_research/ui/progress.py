"""Progress state management helpers.

Handles progress event processing, activity tracking, and UI state updates
during the research pipeline execution.
"""

from datetime import datetime

from a2a_research.models import AgentStatus
from a2a_research.progress import ProgressEvent, ProgressPhase

from .app_state import AppState

_ACTIVITY_MAX_LINES_PER_ROLE = 80


def initialize_progress_state(state: AppState) -> None:
    """Reset progress-related UI state for a fresh run."""
    state.progress_running_substeps = []
    state.current_substep = ""
    state.progress_step_label = "Running the research pipeline…"
    state.activity_by_role = {}
    state.retry_counts = {}
    state.error_counts = {}


def _role_label(role: object) -> str:
    value = getattr(role, "value", str(role))
    return str(value).replace("_", " ").title()


def _format_progress_text(event: ProgressEvent) -> str:
    label = event.substep_label.replace("_", " ").replace(":", ": ")
    parts = [label]
    if event.substep_total and event.substep_total > 1:
        parts.append(f"[{event.substep_index}/{event.substep_total}]")
    if event.detail:
        parts.append(f"— {event.detail}")
    if event.elapsed_ms is not None:
        parts.append(f"({event.elapsed_ms:.0f}ms)")
    return " ".join(parts)


def _append_activity(
    state: AppState, role_label: str, icon: str, text: str
) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"{ts}  {icon}  {text}"
    lines = state.activity_by_role.get(role_label)
    if lines is None:
        lines = []
        state.activity_by_role[role_label] = lines
    lines.append(line)
    if len(lines) > _ACTIVITY_MAX_LINES_PER_ROLE:
        del lines[: len(lines) - _ACTIVITY_MAX_LINES_PER_ROLE]


def apply_progress_event(state: AppState, event: ProgressEvent) -> None:
    """Apply a progress event to update UI state."""
    if event.role is None:
        return
    state.session.ensure_agent_results()
    role_label = _role_label(event.role)
    display = _format_progress_text(event)
    step_result = state.session.get_agent(event.role)

    if event.phase == ProgressPhase.STEP_STARTED:
        state.session.agent_results[event.role] = step_result.model_copy(
            update={"status": AgentStatus.RUNNING, "message": display}
        )
        if role_label not in state.progress_running_substeps:
            state.progress_running_substeps.append(role_label)
        state.progress_step_label = f"{role_label}…"
        _append_activity(state, role_label, "▶", f"started — {display}")
        return

    if event.phase == ProgressPhase.STEP_SUBSTEP:
        state.session.agent_results[event.role] = step_result.model_copy(
            update={"status": AgentStatus.RUNNING, "message": display}
        )
        state.current_substep = display
        state.progress_step_label = f"{role_label}…"
        _append_activity(state, role_label, "·", display)
        if event.substep_label == "rate_limit":
            state.retry_counts[role_label] = (
                state.retry_counts.get(role_label, 0) + 1
            )
        if (
            event.substep_label == "tool_call"
            and "status=error" in event.detail.lower()
        ):
            state.error_counts[role_label] = (
                state.error_counts.get(role_label, 0) + 1
            )
        return

    if event.phase == ProgressPhase.STEP_COMPLETED:
        state.session.agent_results[event.role] = step_result.model_copy(
            update={"status": AgentStatus.COMPLETED, "message": display}
        )
        state.progress_running_substeps = [
            item
            for item in state.progress_running_substeps
            if item != role_label
        ]
        state.progress_step_label = f"{role_label} completed"
        state.current_substep = ""
        _append_activity(state, role_label, "✓", f"completed — {display}")
        return

    if event.phase == ProgressPhase.STEP_FAILED:
        state.session.agent_results[event.role] = step_result.model_copy(
            update={"status": AgentStatus.FAILED, "message": display}
        )
        state.progress_running_substeps = [
            item
            for item in state.progress_running_substeps
            if item != role_label
        ]
        state.progress_step_label = f"{role_label} failed"
        state.current_substep = display
        _append_activity(state, role_label, "✗", f"failed — {display}")
        state.error_counts[role_label] = (
            state.error_counts.get(role_label, 0) + 1
        )
