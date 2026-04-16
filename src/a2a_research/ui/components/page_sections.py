"""Page-level layout sections: header, instructions banner, empty state."""

import mesop as me

from a2a_research.ui.tokens import (
    EMPTY_STATE_STYLE,
    EXAMPLE_QUERY_COLOR,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    FONT_SIZE_TINY,
    HEADER_ACCENT_COLOR,
    HEADER_STYLE,
    HEADER_SUBTITLE_COLOR,
    INSTRUCTIONS_STYLE,
    TEXT_MUTED,
)


@me.component
def PageHeader() -> None:  # noqa: N802
    """Render the page header with title and subtitle."""
    with me.box(style=HEADER_STYLE):
        with me.box(
            style=me.Style(display="flex", align_items="center", gap=10, flex_wrap="wrap")
        ):
            me.text("A2A Research System", type="headline-4")
            me.text(
                "4 agents",
                style=me.Style(
                    font_size=FONT_SIZE_TINY,
                    color=HEADER_ACCENT_COLOR,
                    background="#eff6ff",
                    padding=me.Padding(top=2, bottom=2, left=8, right=8),
                    border_radius=10,
                    border=me.Border(
                        top=me.BorderSide(width=1, color="#bfdbfe"),
                        right=me.BorderSide(width=1, color="#bfdbfe"),
                        bottom=me.BorderSide(width=1, color="#bfdbfe"),
                        left=me.BorderSide(width=1, color="#bfdbfe"),
                    ),
                ),
            )
        me.text(
            "Researcher \u2192 Analyst \u2192 Verifier \u2192 Presenter",
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
            _instruction_step("2", "RAG retrieves", "Pull relevant local sources.")
            _instruction_step("3", "Agents analyze", "Research, verify, and refine claims.")
            _instruction_step("4", "Report renders", "Review sources, claims, and summary.")


@me.component
def PageEmptyState() -> None:  # noqa: N802
    """Render the empty state when no session is active."""
    with me.box(style=EMPTY_STATE_STYLE):
        me.text(
            "\u2315",
            style=me.Style(
                font_size="28px", color=HEADER_ACCENT_COLOR, margin=me.Margin(bottom=8)
            ),
        )
        me.text(
            "Ready to research",
            style=me.Style(font_size="22px", font_weight="bold", margin=me.Margin(bottom=8)),
        )
        me.text(
            "Ask anything. The pipeline will retrieve sources, verify claims, and write a structured report.",
            style=me.Style(
                color=TEXT_MUTED,
                font_size=FONT_SIZE_SUBTITLE,
                margin=me.Margin(bottom=16),
            ),
        )
        me.text(
            "Try one of these example queries",
            style=me.Style(
                font_size=FONT_SIZE_SMALL,
                color=TEXT_MUTED,
                margin=me.Margin(bottom=10),
            ),
        )
        with me.box(
            style=me.Style(
                display="flex",
                justify_content="center",
                gap=8,
                flex_wrap="wrap",
            )
        ):
            _example_query_badge("What is the A2A protocol?")
            _example_query_badge("How do LLM agents collaborate?")
            _example_query_badge("What are RAG evaluation metrics?")


def _instruction_step(number: str, title: str, description: str) -> None:
    with me.box(
        style=me.Style(
            background="#ffffff",
            border=me.Border(
                top=me.BorderSide(width=1, color="#dbeafe"),
                right=me.BorderSide(width=1, color="#dbeafe"),
                bottom=me.BorderSide(width=1, color="#dbeafe"),
                left=me.BorderSide(width=1, color="#dbeafe"),
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
                color="#ffffff",
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


def _example_query_badge(label: str) -> None:
    with me.box(
        style=me.Style(
            border=me.Border(
                top=me.BorderSide(width=1, color="#bfdbfe"),
                right=me.BorderSide(width=1, color="#bfdbfe"),
                bottom=me.BorderSide(width=1, color="#bfdbfe"),
                left=me.BorderSide(width=1, color="#bfdbfe"),
            ),
            border_radius=999,
            background="#ffffff",
            padding=me.Padding(top=8, right=12, bottom=8, left=12),
        )
    ):
        me.text(label, style=me.Style(color=EXAMPLE_QUERY_COLOR, font_size=FONT_SIZE_SMALL))
