"""Page-level layout sections: header, instructions banner, empty state."""

import mesop as me

from a2a_research.ui.tokens import (
    BORDER_WIDTH,
    CARD_RADIUS,
    EMPTY_STATE_BG,
    EMPTY_STATE_BORDER,
    FONT_SIZE_BODY,
    FONT_SIZE_SUBTITLE,
    HEADER_BORDER_COLOR,
    HEADER_BORDER_WIDTH,
    INSTRUCTIONS_BG,
    INSTRUCTIONS_BORDER,
    SECTION_MARGIN_BOTTOM_MD,
    TEXT_MUTED,
)


def render_header() -> None:
    with me.box(
        style=me.Style(
            border=me.Border(
                bottom=me.BorderSide(width=HEADER_BORDER_WIDTH, color=HEADER_BORDER_COLOR),
            ),
            padding=me.Padding(bottom=16),
            margin=me.Margin(bottom=24),
        )
    ):
        me.text("A2A Research System", type="headline-4")
        me.text(
            "Local-first 4-agent pipeline: Researcher → Analyst → Verifier → Presenter",
            style=me.Style(font_size=FONT_SIZE_BODY, color=TEXT_MUTED, margin=me.Margin(top=4)),
        )


def render_instructions() -> None:
    with me.box(
        style=me.Style(
            background=INSTRUCTIONS_BG,
            border=me.Border(
                top=me.BorderSide(width=BORDER_WIDTH, color=INSTRUCTIONS_BORDER),
                right=me.BorderSide(width=BORDER_WIDTH, color=INSTRUCTIONS_BORDER),
                bottom=me.BorderSide(width=BORDER_WIDTH, color=INSTRUCTIONS_BORDER),
                left=me.BorderSide(width=BORDER_WIDTH, color=INSTRUCTIONS_BORDER),
            ),
            border_radius=8,
            padding=me.Padding(top=14, right=14, bottom=14, left=14),
            margin=me.Margin(bottom=24),
        )
    ):
        me.markdown(
            "**How it works:** Enter a research query to start a session. "
            "The pipeline retrieves documents from the RAG corpus, decomposes claims, "
            "verifies evidence, and renders a final markdown report — "
            "all via in-process A2A-shaped agent contracts.",
        )


def render_empty_state() -> None:
    with me.box(
        style=me.Style(
            text_align="center",
            background=EMPTY_STATE_BG,
            border=me.Border(
                top=me.BorderSide(width=BORDER_WIDTH, color=EMPTY_STATE_BORDER),
                right=me.BorderSide(width=BORDER_WIDTH, color=EMPTY_STATE_BORDER),
                bottom=me.BorderSide(width=BORDER_WIDTH, color=EMPTY_STATE_BORDER),
                left=me.BorderSide(width=BORDER_WIDTH, color=EMPTY_STATE_BORDER),
            ),
            border_radius=CARD_RADIUS,
            padding=me.Padding(top=48, right=24, bottom=48, left=24),
            margin=me.Margin(bottom=SECTION_MARGIN_BOTTOM_MD),
        )
    ):
        me.text(
            "No active session — enter a query above to begin.",
            style=me.Style(color=TEXT_MUTED, font_size=FONT_SIZE_SUBTITLE),
        )
