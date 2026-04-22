"""Shared helpers for UI app tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from a2a_research.models import ResearchSession


async def _drain_on_submit(
    app_mod, mock_event: MagicMock | None = None
) -> None:
    agen = app_mod._on_submit(mock_event or MagicMock())
    async for _ in agen:
        pass


def _make_state(
    query_text: str = "",
    loading: bool = False,
    session: ResearchSession | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        query_text=query_text,
        loading=loading,
        session=session or ResearchSession(),
        progress_granularity=1,
        current_substep="",
        progress_pct=0.0,
        progress_step_label="",
        progress_running_substeps=[],
    )
