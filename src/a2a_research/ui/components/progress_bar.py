"""Overall progress bar with step and sub-step labels."""

import mesop as me

from a2a_research.ui.tokens import (
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    LOADING_TEXT,
    PROGRESS_BAR_BG,
    PROGRESS_BAR_FILL,
    PROGRESS_BAR_HEIGHT,
    SUBSTEP_COLOR,
)


@me.component
def ProgressBar(  # noqa: N802
    pct: float,
    step_label: str,
    substep_label: str,
) -> None:
    """Horizontal fill bar plus step title and optional sub-step line."""
    pct_clamped = max(0.0, min(1.0, float(pct)))
    fill_pct = round(pct_clamped * 100)
    fill_width = f"{fill_pct}%"

    with me.box(style=me.Style(width="100%")):
        me.text(
            f"{fill_pct}%",
            style=me.Style(
                font_size=FONT_SIZE_SUBTITLE,
                color=LOADING_TEXT,
                font_weight="bold",
                margin=me.Margin(bottom=8),
            ),
        )
        with me.box(
            style=me.Style(
                width="100%",
                height=PROGRESS_BAR_HEIGHT,
                background=PROGRESS_BAR_BG,
                border_radius=6,
                overflow="hidden",
            )
        ), me.box(
            style=me.Style(
                height="100%",
                width=fill_width,
                background=f"linear-gradient(90deg, {PROGRESS_BAR_FILL}, #22c55e)",
                border_radius=6,
                transition="width 0.2s ease-out",
            )
        ):
            pass
        me.text(
            step_label,
            style=me.Style(
                font_size=FONT_SIZE_SUBTITLE,
                color=LOADING_TEXT,
                font_weight="bold",
                margin=me.Margin(top=14, bottom=4),
            ),
        )
        if substep_label:
            me.text(
                substep_label,
                style=me.Style(font_size=FONT_SIZE_SMALL, color=SUBSTEP_COLOR),
            )
        else:
            me.text(
                "\u00a0",
                style=me.Style(font_size=FONT_SIZE_SMALL, color=SUBSTEP_COLOR),
            )
