"""Application state class and snapshot utilities.

``AppState.session`` is always a :class:`~a2a_research.models.ResearchSession`
so Mesop registers the Pydantic model for serialization (union-typed session
fields are skipped and break round-trips).
"""

import dataclasses
from typing import Any

import mesop as me

from a2a_research.models import ResearchSession


@me.stateclass
class AppState:
    query_text: str = ""
    session: ResearchSession = dataclasses.field(
        default_factory=ResearchSession
    )
    loading: bool = False
    current_substep: str = ""
    progress_step_label: str = ""
    progress_running_substeps: list[str] = dataclasses.field(
        default_factory=list
    )
    # Per-role activity feed: role label → list of "HH:MM:SS  text" lines,
    # appended on every progress event. Drives the live per-agent activity
    # panel that replaced the coarse percentage bar.
    activity_by_role: dict[str, list[str]] = dataclasses.field(
        default_factory=dict
    )
    show_verbose_prompts: bool = True
    retry_counts: dict[str, int] = dataclasses.field(default_factory=dict)
    error_counts: dict[str, int] = dataclasses.field(default_factory=dict)


def state_snapshot(state: AppState) -> dict[str, object]:
    """Create a serializable snapshot of the current state for logging."""
    activity_by_role = getattr(state, "activity_by_role", {})
    return {
        "query_text": state.query_text,
        "loading": state.loading,
        "progress_step_label": state.progress_step_label,
        "current_substep": state.current_substep,
        "running_substeps": list(state.progress_running_substeps),
        "activity_counts": {
            role: len(lines) for role, lines in activity_by_role.items()
        },
        "session": {
            "id": state.session.id,
            "query": state.session.query,
            "roles": [role.value for role in state.session.roles],
            "agent_statuses": {
                role.value: result.status.value
                for role, result in state.session.agent_results.items()
            },
            "final_report_chars": len(state.session.final_report),
            "error": state.session.error,
        },
    }
