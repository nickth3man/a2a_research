"""Design token style presets for common UI patterns."""

import mesop as me

from a2a_research.ui.tokens import (
    BORDER_WIDTH,
    CALLOUT_RADIUS,
    CARD_RADIUS,
    ERROR_BANNER_BG,
    ERROR_BANNER_BORDER,
    ERROR_TEXT,
    HEADER_ACCENT_COLOR,
    HEADER_BORDER_COLOR,
    HEADER_BORDER_WIDTH,
    INSTRUCTIONS_BG,
    INSTRUCTIONS_BORDER,
    LOADING_BG,
    LOADING_BORDER,
    SECTION_MARGIN_BOTTOM_MD,
)


def _build_border(color: str) -> me.Border:
    """Build a border with the given color on all sides."""
    side = me.BorderSide(width=BORDER_WIDTH, color=color)
    return me.Border(top=side, right=side, bottom=side, left=side)


ERROR_BANNER_STYLE = me.Style(
    background=ERROR_BANNER_BG,
    border=me.Border(
        left=me.BorderSide(width=4, color=ERROR_TEXT),
        top=me.BorderSide(width=BORDER_WIDTH, color=ERROR_BANNER_BORDER),
        right=me.BorderSide(width=BORDER_WIDTH, color=ERROR_BANNER_BORDER),
        bottom=me.BorderSide(width=BORDER_WIDTH, color=ERROR_BANNER_BORDER),
    ),
    border_radius=CALLOUT_RADIUS,
    padding=me.Padding(top=14, right=14, bottom=14, left=14),
    margin=me.Margin(bottom=16),
    display="flex",
    align_items="center",
    gap=12,
)

LOADING_CARD_STYLE = me.Style(
    text_align="center",
    background=LOADING_BG,
    border=_build_border(LOADING_BORDER),
    border_radius=CARD_RADIUS,
    padding=me.Padding(top=32, right=32, bottom=32, left=32),
    margin=me.Margin(bottom=SECTION_MARGIN_BOTTOM_MD),
)

HEADER_STYLE = me.Style(
    border=me.Border(
        left=me.BorderSide(width=4, color=HEADER_ACCENT_COLOR),
        bottom=me.BorderSide(
            width=HEADER_BORDER_WIDTH, color=HEADER_BORDER_COLOR
        ),
    ),
    padding=me.Padding(left=16, bottom=16),
    margin=me.Margin(bottom=24),
)

INSTRUCTIONS_STYLE = me.Style(
    background=INSTRUCTIONS_BG,
    border=_build_border(INSTRUCTIONS_BORDER),
    border_radius=8,
    padding=me.Padding(top=14, right=14, bottom=14, left=14),
    margin=me.Margin(bottom=24),
)

EMPTY_STATE_STYLE = me.Style(
    text_align="center",
    background="#f9fafb",
    border=_build_border("#d1d5db"),
    border_radius=CARD_RADIUS,
    padding=me.Padding(top=48, right=24, bottom=48, left=24),
    margin=me.Margin(bottom=SECTION_MARGIN_BOTTOM_MD),
)
