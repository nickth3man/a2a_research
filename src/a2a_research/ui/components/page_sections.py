"""Page-level layout sections: header, instructions banner, empty state."""

import mesop as me

from a2a_research.ui.tokens import (
    CARD_BACKGROUND,
    EMPTY_STATE_ICON_BG,
    EMPTY_STATE_ICON_SIZE,
    EMPTY_STATE_STYLE,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    FONT_SIZE_TINY,
    HEADER_ACCENT_COLOR,
    HEADER_STYLE,
    HEADER_SUBTITLE_COLOR,
    INSTRUCTIONS_BG,
    INSTRUCTIONS_BORDER,
    INSTRUCTIONS_STYLE,
    STEP_CARD_BORDER,
    TEXT_MUTED,
)


@me.component
def PageHeader() -> None:  # noqa: N802
    """Render the page header with title and subtitle."""
    with me.box(style=HEADER_STYLE):
        with me.box(
            style=me.Style(display="flex", align_items="center", gap=10, flex_wrap="nowrap")
        ):
            me.text(
                "A2A Research System",
                type="headline-4",
                style=me.Style(display="inline-block", white_space="nowrap"),
            )
            me.text(
                "5 agents",
                style=me.Style(
                    font_size=FONT_SIZE_TINY,
                    color=HEADER_ACCENT_COLOR,
                    background=INSTRUCTIONS_BG,
                    padding=me.Padding(top=2, bottom=2, left=8, right=8),
                    border_radius=10,
                    border=me.Border(
                        top=me.BorderSide(width=1, color=INSTRUCTIONS_BORDER),
                        right=me.BorderSide(width=1, color=INSTRUCTIONS_BORDER),
                        bottom=me.BorderSide(width=1, color=INSTRUCTIONS_BORDER),
                        left=me.BorderSide(width=1, color=INSTRUCTIONS_BORDER),
                    ),
                    flex_shrink=0,
                ),
            )
        me.text(
            "Planner \u2192 Searcher \u2192 Reader \u2192 FactChecker \u2192 Synthesizer",
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
                font_size=FONT_SIZE_BODY, font_weight="bold", margin=me.Margin(bottom=12)
            ),
        )
        with me.box(style=me.Style(display="flex", gap=8, flex_wrap="wrap")):
            _instruction_step("1", "Enter a query", "Start a research session.")
            _instruction_step(
                "2", "Sources retrieved", "Pull relevant documents from the local corpus."
            )
            _instruction_step("3", "Agents analyze", "Research, verify, and refine claims.")
            _instruction_step("4", "Report renders", "Review sources, claims, and summary.")


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
            style=me.Style(font_size="24px", font_weight="bold", margin=me.Margin(bottom=8)),
        )
        me.text(
            "Ask about topics in the local corpus. The pipeline retrieves relevant sources, verifies claims, and writes a structured report.",
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


def _instruction_step(number: str, title: str, description: str) -> None:
    with me.box(
        style=me.Style(
            background=CARD_BACKGROUND,
            border=me.Border(
                top=me.BorderSide(width=1, color=STEP_CARD_BORDER),
                right=me.BorderSide(width=1, color=STEP_CARD_BORDER),
                bottom=me.BorderSide(width=1, color=STEP_CARD_BORDER),
                left=me.BorderSide(width=1, color=STEP_CARD_BORDER),
            ),
            border_radius=8,
            padding=me.Padding(top=10, right=12, bottom=10, left=12),
            display="flex",
            gap=10,
            align_items="flex-start",
            flex="1 1 180px",
            min_width=180,
        )
    ):
        with me.box(
            style=me.Style(
                background=HEADER_ACCENT_COLOR,
                color=CARD_BACKGROUND,
                width=24,
                height=24,
                border_radius=12,
                display="flex",
                align_items="center",
                justify_content="center",
                font_size=FONT_SIZE_TINY,
                font_weight="bold",
                flex_shrink=0,
            )
        ):
            me.text(number)
        with me.box(style=me.Style(text_align="left")):
            me.text(title, style=me.Style(font_size=FONT_SIZE_BODY, font_weight="bold"))
            me.text(
                description,
                style=me.Style(
                    font_size=FONT_SIZE_SMALL, color=TEXT_MUTED, margin=me.Margin(top=4)
                ),
            )
