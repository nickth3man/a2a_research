"""Research query input card and submit control."""

from collections.abc import Callable
from typing import Any, cast

import mesop as me

from a2a_research.ui.primitives import query_input_card_style
from a2a_research.ui.tokens import SUBTITLE_MARGIN_BOTTOM


@me.component
def CardQueryInput(  # noqa: N802
    on_submit: Callable[[Any], Any],
    on_query_input: Callable[[Any], Any],
    *,
    submit_disabled: int = 0,
) -> None:
    """Render the query input card with textarea and submit button."""
    with me.box(style=query_input_card_style()):
        me.text(
            "Research Query",
            type="subtitle-1",
            style=me.Style(margin=SUBTITLE_MARGIN_BOTTOM),
        )
        me.textarea(
            label="Enter your research question\u2026",
            key="query",
            rows=3,
            on_input=on_query_input,
            style=me.Style(margin=SUBTITLE_MARGIN_BOTTOM),
        )
        with me.box(style=me.Style(display="flex", justify_content="end")):
            me.button(
                "Run Research",
                on_click=on_submit,
                type="flat",
                color="primary",
                disabled=cast("bool", submit_disabled),
            )
