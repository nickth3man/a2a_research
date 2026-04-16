"""Research query input card and submit control."""

from collections.abc import Callable
from typing import Any, cast

import mesop as me

from a2a_research.ui.components.granularity_toggle import GranularityToggle
from a2a_research.ui.primitives import get_query_input_card_style
from a2a_research.ui.tokens import SUBTITLE_MARGIN_BOTTOM


def CardQueryInput(  # noqa: N802
    on_submit: Callable[[Any], Any],
    on_query_input: Callable[[Any], Any],
    *,
    query_text: str = "",
    submit_disabled: int = 0,
    progress_granularity: int = 1,
    on_granularity_agent: Callable[[Any], Any] | None = None,
    on_granularity_substep: Callable[[Any], Any] | None = None,
    on_granularity_detail: Callable[[Any], Any] | None = None,
    on_example_a: Callable[[Any], Any] | None = None,
    on_example_b: Callable[[Any], Any] | None = None,
    on_example_c: Callable[[Any], Any] | None = None,
) -> None:
    """Render the query input card with textarea and submit button."""
    with me.box(style=get_query_input_card_style()):
        me.text(
            "Research Query",
            type="subtitle-1",
            style=me.Style(margin=SUBTITLE_MARGIN_BOTTOM),
        )
        if on_example_a and on_example_b and on_example_c:
            me.text(
                "Example queries",
                style=me.Style(font_size="12px", color="#6b7280", margin=me.Margin(bottom=8)),
            )
            with me.box(
                style=me.Style(
                    display="flex", gap=8, flex_wrap="wrap", margin=me.Margin(bottom=12)
                )
            ):
                me.button(
                    "What is the A2A protocol?",
                    on_click=on_example_a,
                    type="stroked",
                    color="accent",
                )
                me.button(
                    "How do LLM agents collaborate?",
                    on_click=on_example_b,
                    type="stroked",
                    color="accent",
                )
                me.button(
                    "What are RAG evaluation metrics?",
                    on_click=on_example_c,
                    type="stroked",
                    color="accent",
                )
        if on_granularity_agent and on_granularity_substep and on_granularity_detail:
            with me.box(
                style=me.Style(
                    margin=me.Margin(bottom=12),
                    padding=me.Padding(bottom=12),
                    border=me.Border(
                        bottom=me.BorderSide(width=1, color="#e5e7eb"),
                    ),
                )
            ):
                me.text(
                    "Pipeline settings",
                    style=me.Style(
                        font_size="12px",
                        color="#6b7280",
                        font_weight="bold",
                        margin=me.Margin(bottom=8),
                    ),
                )
            GranularityToggle(
                current=progress_granularity,
                on_agent_level=on_granularity_agent,
                on_substep_level=on_granularity_substep,
                on_detail_level=on_granularity_detail,
            )
        me.textarea(
            label="Enter your research question\u2026",
            key="query",
            value=query_text,
            rows=4,
            on_input=on_query_input,
            style=me.Style(width="100%", margin=SUBTITLE_MARGIN_BOTTOM),
        )
        with me.box(style=me.Style(display="flex", justify_content="end")):
            me.button(
                "Run Research",
                on_click=on_submit,
                type="flat",
                color="primary",
                disabled=cast("bool", submit_disabled),
            )
