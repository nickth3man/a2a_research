"""Error and loading banners."""

import mesop as me

from a2a_research.models import ResearchSession
from a2a_research.ui.components.timeline import agent_timeline_card
from a2a_research.ui.tokens import (
    CALLOUT_RADIUS,
    CARD_RADIUS,
    ERROR_BANNER_BG,
    ERROR_BANNER_BORDER,
    ERROR_TEXT,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    LOADING_BG,
    LOADING_BORDER,
    LOADING_TEXT,
    SECTION_MARGIN_BOTTOM_MD,
)


@me.component
def error_banner(error: str) -> None:
    with me.box(
        style=me.Style(
            background=ERROR_BANNER_BG,
            border=me.Border(
                top=me.BorderSide(width=1, color=ERROR_BANNER_BORDER),
                right=me.BorderSide(width=1, color=ERROR_BANNER_BORDER),
                bottom=me.BorderSide(width=1, color=ERROR_BANNER_BORDER),
                left=me.BorderSide(width=1, color=ERROR_BANNER_BORDER),
            ),
            border_radius=CALLOUT_RADIUS,
            padding=me.Padding(top=14, right=14, bottom=14, left=14),
            margin=me.Margin(bottom=16),
            display="flex",
            align_items="center",
            gap=12,
        )
    ):
        me.text(
            _error_banner_message(error),
            style=me.Style(color=ERROR_TEXT, font_size=FONT_SIZE_BODY),
        )


def _error_banner_message(error: str, *, max_len: int = 200) -> str:
    prefix = "Pipeline error: "
    if len(error) <= max_len:
        return prefix + error
    return prefix + error[:max_len] + "…"


@me.component
def loading_card(session: ResearchSession) -> None:
    with me.box(
        style=me.Style(
            text_align="center",
            background=LOADING_BG,
            border=me.Border(
                top=me.BorderSide(width=1, color=LOADING_BORDER),
                right=me.BorderSide(width=1, color=LOADING_BORDER),
                bottom=me.BorderSide(width=1, color=LOADING_BORDER),
                left=me.BorderSide(width=1, color=LOADING_BORDER),
            ),
            border_radius=CARD_RADIUS,
            padding=me.Padding(top=32, right=32, bottom=32, left=32),
            margin=me.Margin(bottom=SECTION_MARGIN_BOTTOM_MD),
        )
    ):
        me.text(
            "Running research pipeline…",
            style=me.Style(font_size=FONT_SIZE_SUBTITLE, color=LOADING_TEXT, font_weight="bold"),
        )
        me.text(
            "Researchers retrieving documents · Analysts decomposing · "
            "Verifiers checking evidence · Presenter rendering",
            style=me.Style(font_size=FONT_SIZE_SMALL, color=LOADING_TEXT, margin=me.Margin(top=8)),
        )
    agent_timeline_card(session)
