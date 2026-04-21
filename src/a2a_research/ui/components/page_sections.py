"""Page-level layout sections: header, instructions banner, empty state."""

import mesop as me

from a2a_research.ui.components.page_section_helpers import (
    INSTRUCTION_STEPS,
    _instruction_step,
)
from a2a_research.ui.style_presets import (
    EMPTY_STATE_STYLE,
    HEADER_STYLE,
    INSTRUCTIONS_STYLE,
)
from a2a_research.ui.tokens import (
    EMPTY_STATE_ICON_BG,
    EMPTY_STATE_ICON_SIZE,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    HEADER_ACCENT_COLOR,
    HEADER_SUBTITLE_COLOR,
    TEXT_MUTED,
)


@me.component
def PageHeader() -> None:  # noqa: N802
    """Render the page header with title and subtitle."""
    with me.box(style=HEADER_STYLE):
        with me.box(
            style=me.Style(
                display="flex",
                align_items="center",
                gap=10,
                flex_wrap="nowrap",
            )
        ):
            me.text(
                "A2A Research System",
                type="headline-4",
                style=me.Style(display="inline-block", white_space="nowrap"),
            )
            me.text(
                "5 agents",
                style=me.Style(
                    font_size="12px",
                    color=HEADER_ACCENT_COLOR,
                    background="#f0f9ff",
                    padding=me.Padding(top=2, bottom=2, left=8, right=8),
                    border_radius=10,
                    border=me.Border.all(
                        me.BorderSide(width=1, color="#bae6fd")
                    ),
                    flex_shrink=0,
                ),
            )
        me.text(
            (
                "Planner \u2192 Searcher \u2192 Reader"
                " \u2192 FactChecker \u2192 Synthesizer"
            ),
            style=me.Style(
                font_size=FONT_SIZE_BODY,
                color=HEADER_SUBTITLE_COLOR,
                margin=me.Margin(top=6),
            ),
        )


@me.component
def PageInstructions() -> None:  # noqa: N802
    """Render the instructions banner explaining how the system works."""
    with me.box(style=INSTRUCTIONS_STYLE):
        me.text(
            "How it works",
            style=me.Style(
                font_size=FONT_SIZE_BODY,
                font_weight="bold",
                margin=me.Margin(bottom=12),
            ),
        )
        with me.box(style=me.Style(display="flex", gap=8, flex_wrap="wrap")):
            for number, title, description in INSTRUCTION_STEPS:
                _instruction_step(number, title, description)


@me.component
def PageEmptyState() -> None:  # noqa: N802
    """Render the empty state when no session is active."""
    with me.box(style=EMPTY_STATE_STYLE):
        with me.box(
            style=me.Style(
                width=64,
                height=64,
                border_radius="50%",
                background=EMPTY_STATE_ICON_BG,
                display="flex",
                align_items="center",
                justify_content="center",
                margin=me.Margin(bottom=12, left="auto", right="auto"),
            )
        ):
            me.icon(
                "search",
                style=me.Style(
                    font_size=EMPTY_STATE_ICON_SIZE,
                    color=HEADER_ACCENT_COLOR,
                ),
            )
        me.text(
            "Ready to research",
            style=me.Style(
                font_size="24px",
                font_weight="bold",
                margin=me.Margin(bottom=8),
            ),
        )
        me.text(
            (
                "Ask about topics in the local corpus. The pipeline"
                " retrieves relevant sources, verifies claims, and writes a"
                " structured report."
            ),
            style=me.Style(
                color=TEXT_MUTED,
                font_size=FONT_SIZE_SUBTITLE,
                margin=me.Margin(bottom=16),
            ),
        )
        me.text(
            "Use the example queries below to get started",
            style=me.Style(
                font_size=FONT_SIZE_SMALL,
                color=TEXT_MUTED,
                font_weight=500,
            ),
        )
