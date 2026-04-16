"""Research query input card and submit control."""

from collections.abc import Callable
from typing import Any, cast

import mesop as me

from a2a_research.ui.components.granularity_toggle import GranularityToggle
from a2a_research.ui.primitives import get_query_input_card_style
from a2a_research.ui.tokens import (
    BORDER_COLOR,
    CHIP_BG,
    CHIP_BORDER,
    CHIP_RADIUS,
    CHIP_TEXT_COLOR,
    EXAMPLE_QUERIES,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    SUBMIT_BUTTON_PADDING,
    SUBTITLE_MARGIN_BOTTOM,
    TEXT_MUTED,
)

_CHIP_STYLE = me.Style(
    display="inline-flex",
    align_items="center",
    gap=4,
    padding=me.Padding(top=6, right=14, bottom=6, left=12),
    border_radius=CHIP_RADIUS,
    background=CHIP_BG,
    border=me.Border(
        top=me.BorderSide(width=1, color=CHIP_BORDER),
        right=me.BorderSide(width=1, color=CHIP_BORDER),
        bottom=me.BorderSide(width=1, color=CHIP_BORDER),
        left=me.BorderSide(width=1, color=CHIP_BORDER),
    ),
    cursor="pointer",
    font_size=FONT_SIZE_SMALL,
    color=CHIP_TEXT_COLOR,
    font_weight=500,
)


def CardQueryInput(  # noqa: N802
    on_submit: Callable[[Any], Any],
    on_query_input: Callable[[Any], Any],
    *,
    query_text: str = "",
    submit_disabled: bool = False,
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
            with me.box(
                style=me.Style(
                    display="flex",
                    align_items="center",
                    gap=4,
                    margin=me.Margin(bottom=8),
                )
            ):
                me.icon(
                    "lightbulb",
                    style=me.Style(font_size="14px", color=TEXT_MUTED),
                )
                me.text(
                    "Example queries",
                    style=me.Style(
                        font_size=FONT_SIZE_SMALL,
                        color=TEXT_MUTED,
                    ),
                )
            with me.box(
                style=me.Style(
                    display="flex", gap=8, flex_wrap="wrap", margin=me.Margin(bottom=12)
                )
            ):
                for example_query, handler in (
                    (EXAMPLE_QUERIES[0], on_example_a),
                    (EXAMPLE_QUERIES[1], on_example_b),
                    (EXAMPLE_QUERIES[2], on_example_c),
                ):
                    me.button(
                        example_query,
                        on_click=handler,
                        type="stroked",
                        style=_CHIP_STYLE,
                    )
        if on_granularity_agent and on_granularity_substep and on_granularity_detail:
            with me.box(
                style=me.Style(
                    margin=me.Margin(bottom=12),
                    padding=me.Padding(bottom=12),
                    border=me.Border(
                        bottom=me.BorderSide(width=1, color=BORDER_COLOR),
                    ),
                )
            ):
                me.text(
                    "Pipeline settings",
                    style=me.Style(
                        font_size=FONT_SIZE_SMALL,
                        color=TEXT_MUTED,
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
            appearance="outline",
            on_input=on_query_input,
            shortcuts={me.Shortcut(key="Enter", ctrl=True): on_submit},
            style=me.Style(width="100%", margin=SUBTITLE_MARGIN_BOTTOM),
        )
        with me.box(
            style=me.Style(
                display="flex",
                align_items="center",
                justify_content="end",
                gap=8,
                padding=SUBMIT_BUTTON_PADDING,
            )
        ):
            # Mesop's current button disabled code path still expects an int-backed
            # CodeValue during serialization, even though the public API is typed as bool.
            button_style = (
                me.Style(
                    background="linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
                    color="#fff",
                )
                if not submit_disabled
                else me.Style()
            )
            me.button(
                "Running\u2026" if submit_disabled else "Run Research",
                on_click=on_submit,
                type="flat",
                color="primary",
                disabled=cast("bool", int(submit_disabled)),
                style=button_style,
            )
        if submit_disabled:
            me.text(
                "Pipeline running\u2026",
                style=me.Style(
                    font_size=FONT_SIZE_TINY,
                    color=TEXT_MUTED,
                    text_align="end",
                    margin=me.Margin(top=4),
                ),
            )
