"""A / B / C control for progress update verbosity."""

from collections.abc import Callable
from typing import Any

import mesop as me

from a2a_research.ui.tokens import (
    FONT_SIZE_SMALL,
    GRANULARITY_GROUP_BG,
    GRANULARITY_SELECTED_BG,
    GRANULARITY_SELECTED_SHADOW,
    TEXT_MUTED,
)


def GranularityToggle(  # noqa: N802
    current: int,
    on_agent_level: Callable[[Any], Any],
    on_substep_level: Callable[[Any], Any],
    on_detail_level: Callable[[Any], Any],
) -> None:
    """Three-way toggle: agent-only, sub-steps, or maximum detail."""
    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=6,
            margin=me.Margin(bottom=12),
        )
    ):
        me.text(
            "Pipeline detail level",
            style=me.Style(font_size=FONT_SIZE_SMALL, color=TEXT_MUTED),
        )
        with me.box(
            style=me.Style(
                display="flex",
                gap=4,
                flex_wrap="wrap",
                background=GRANULARITY_GROUP_BG,
                border_radius=8,
                padding=me.Padding(top=4, right=4, bottom=4, left=4),
            )
        ):
            _render_granularity_button("Agents only", current == 1, on_agent_level)
            _render_granularity_button("With steps", current == 2, on_substep_level)
            _render_granularity_button("Detail", current == 3, on_detail_level)


def _render_granularity_button(
    label: str,
    is_selected: bool,
    handler: Callable[[Any], Any],
) -> None:
    with me.box(
        style=me.Style(
            background=GRANULARITY_SELECTED_BG if is_selected else "transparent",
            border_radius=6,
            box_shadow=GRANULARITY_SELECTED_SHADOW if is_selected else None,
        )
    ):
        me.button(
            label,
            on_click=handler,
            type="flat",
            color="primary" if is_selected else "accent",
        )
