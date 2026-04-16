"""Error and loading banners."""

from collections.abc import Callable
from typing import Any

import mesop as me

from a2a_research.models import ResearchSession
from a2a_research.ui.components.progress_bar import ProgressBar
from a2a_research.ui.components.step_checklist import StepChecklist
from a2a_research.ui.tokens import (
    ERROR_BANNER_STYLE,
    ERROR_ICON_COLOR,
    ERROR_TEXT,
    LOADING_CARD_STYLE,
    LOADING_DOT_SIZE,
)


@me.component
def BannerError(  # noqa: N802
    error: str, *, on_retry: Callable[[Any], Any] | None = None
) -> None:
    """Display an error banner with left-border accent and retry action."""
    with me.box(style=ERROR_BANNER_STYLE):
        me.icon(
            "error_outline",
            style=me.Style(
                font_size="20px",
                color=ERROR_ICON_COLOR,
                flex_shrink=0,
            ),
        )
        me.text(
            _error_banner_message(error),
            style=me.Style(
                color=ERROR_TEXT,
                font_size="15px",
                font_weight=500,
                flex_grow=1,
            ),
        )
        if on_retry is not None:
            me.button("Retry", on_click=on_retry, type="flat", color="warn")


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
        with me.box(
            style=me.Style(
                width="100%",
                margin=me.Margin(bottom=12),
                display="flex",
                align_items="center",
                justify_content="center",
                gap=8,
            )
        ):
            with me.box(
                style=me.Style(
                    width=LOADING_DOT_SIZE,
                    height=LOADING_DOT_SIZE,
                    border_radius="9999px",
                    background="#f59e0b",
                    box_shadow="0 0 0 4px rgba(245, 158, 11, 0.25), 0 0 12px 2px rgba(245, 158, 11, 0.35)",
                )
            ):
                pass
            me.text(
                progress_step_label or "Pipeline starting",
                style=me.Style(font_weight="bold", font_size="13px", color="#92400e"),
            )
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
