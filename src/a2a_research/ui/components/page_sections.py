"""Page-level layout sections: header, instructions banner, empty state."""

import mesop as me

from a2a_research.ui.tokens import (
    EMPTY_STATE_STYLE,
    FONT_SIZE_BODY,
    FONT_SIZE_SUBTITLE,
    HEADER_STYLE,
    INSTRUCTIONS_STYLE,
    TEXT_MUTED,
)


@me.component
def PageHeader() -> None:  # noqa: N802
    """Render the page header with title and subtitle."""
    with me.box(style=HEADER_STYLE):
        me.text("A2A Research System", type="headline-4")
        me.text(
            "Local-first 4-agent pipeline: Researcher \u2192 Analyst \u2192 Verifier \u2192 Presenter",
            style=me.Style(font_size=FONT_SIZE_BODY, color=TEXT_MUTED, margin=me.Margin(top=4)),
        )


@me.component
def PageInstructions() -> None:  # noqa: N802
    """Render the instructions banner explaining how the system works."""
    with me.box(style=INSTRUCTIONS_STYLE):
        me.markdown(
            "**How it works:** Enter a research query to start a session. "
            "The pipeline retrieves documents from the RAG corpus, decomposes claims, "
            "verifies evidence, and renders a final markdown report \u2014 "
            "all via in-process A2A-shaped agent contracts.",
        )


@me.component
def PageEmptyState() -> None:  # noqa: N802
    """Render the empty state when no session is active."""
    with me.box(style=EMPTY_STATE_STYLE):
        me.text(
            "No active session \u2014 enter a query above to begin.",
            style=me.Style(color=TEXT_MUTED, font_size=FONT_SIZE_SUBTITLE),
        )
