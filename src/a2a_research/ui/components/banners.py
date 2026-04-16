"""Error and loading banners."""

import mesop as me

from a2a_research.ui.tokens import (
    ERROR_BANNER_STYLE,
    ERROR_TEXT,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_SUBTITLE,
    LOADING_CARD_STYLE,
    LOADING_TEXT,
)


@me.component
def BannerError(error: str) -> None:  # noqa: N802
    """Display an error banner with standardized styling."""
    with me.box(style=ERROR_BANNER_STYLE):
        me.text(
            _error_banner_message(error),
            style=me.Style(color=ERROR_TEXT, font_size=FONT_SIZE_BODY),
        )


def _error_banner_message(error: str, *, max_len: int = 200) -> str:
    """Format an error message with prefix and length limit."""
    prefix = "Pipeline error: "
    if len(error) <= max_len:
        return prefix + error
    return prefix + error[:max_len] + "\u2026"


@me.component
def CardLoading() -> None:  # noqa: N802
    """Display a loading card with progress messaging."""
    with me.box(style=LOADING_CARD_STYLE):
        me.text(
            "Running research pipeline\u2026",
            style=me.Style(font_size=FONT_SIZE_SUBTITLE, color=LOADING_TEXT, font_weight="bold"),
        )
        me.text(
            "Researchers retrieving documents \u00b7 Analysts decomposing \u00b7 "
            "Verifiers checking evidence \u00b7 Presenter rendering",
            style=me.Style(font_size=FONT_SIZE_SMALL, color=LOADING_TEXT, margin=me.Margin(top=8)),
        )
