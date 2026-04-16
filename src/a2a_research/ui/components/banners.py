"""Error and loading banners."""

import mesop as me

from a2a_research.models import ResearchSession
from a2a_research.ui.components.progress_bar import ProgressBar
from a2a_research.ui.components.step_checklist import StepChecklist
from a2a_research.ui.tokens import (
    ERROR_BANNER_STYLE,
    ERROR_TEXT,
    FONT_SIZE_BODY,
    LOADING_CARD_STYLE,
)


@me.component
def BannerError(error: str) -> None:  # noqa: N802
    """Display an error banner with standardized styling."""
    with me.box(style=ERROR_BANNER_STYLE):
        me.text(
            _error_banner_message(error),
            style=me.Style(color=ERROR_TEXT, font_size=FONT_SIZE_BODY),
        )


def _error_banner_message(error: str, *, max_length: int = 200) -> str:
    """Format an error message with prefix and length limit."""
    prefix = "Pipeline error: "
    if len(error) <= max_length:
        return prefix + error
    return prefix + error[:max_length] + "\u2026"


@me.component
def CardLoading(  # noqa: N802
    progress_pct: float,
    progress_step_label: str,
    progress_substep_label: str,
    session: ResearchSession,
    granularity: int,
    running_substeps: list[str],
) -> None:
    """Live progress bar and agent checklist while the pipeline runs."""
    with me.box(style=LOADING_CARD_STYLE):
        ProgressBar(
            pct=progress_pct,
            step_label=progress_step_label or "In progress\u2026",
            substep_label=progress_substep_label,
        )
        me.box(style=me.Style(height=20))
        StepChecklist(
            session=session,
            granularity=granularity,
            running_substeps=running_substeps,
        )
