"""Overall progress bar with step and sub-step labels."""

import mesop as me

from a2a_research.ui.tokens import (
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    LOADING_TEXT,
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

    with me.box(style=me.Style(width="100%")):
        me.text(
            f"{fill_pct}%",
            style=me.Style(
                font_size="18px",
                color=LOADING_TEXT,
                font_weight="bold",
                margin=me.Margin(bottom=8),
            ),
        )
        me.progress_bar(value=fill_pct, mode="determinate", color="primary")
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
