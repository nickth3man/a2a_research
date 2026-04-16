"""Mesop ``AppState`` shared by the main page and UI components."""

from __future__ import annotations

from dataclasses import field

import mesop as me

from a2a_research.models import ResearchSession


@me.stateclass
class AppState:
    query_text: str = ""
    session: ResearchSession = field(default_factory=ResearchSession)
    loading: bool = False
    progress_granularity: int = 1
    current_substep: str = ""
    progress_pct: float = 0.0
    progress_step_label: str = ""
    progress_running_substeps: list[str] = field(default_factory=list)
