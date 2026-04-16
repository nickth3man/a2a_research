"""A / B / C control for progress update verbosity."""

from collections.abc import Callable
from typing import Any

import mesop as me

from a2a_research.ui.tokens import FONT_SIZE_SMALL, TEXT_MUTED


@me.component
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
            "Progress detail: A = agents \u00b7 B = sub-steps \u00b7 C = full detail",
            style=me.Style(font_size=FONT_SIZE_SMALL, color=TEXT_MUTED),
        )
        with me.box(style=me.Style(display="flex", gap=8, flex_wrap="wrap")):
            _gran_button("A", "Agent steps", current == 1, on_agent_level)
            _gran_button("B", "Sub-steps", current == 2, on_substep_level)
            _gran_button("C", "Maximum", current == 3, on_detail_level)


def _gran_button(
    short: str,
    subtitle: str,
    selected: bool,
    handler: Callable[[Any], Any],
) -> None:
    color = "primary" if selected else "accent"
    with me.box(style=me.Style(display="flex", flex_direction="column", align_items="center")):
        me.button(f"{short}", on_click=handler, type="flat", color=color)
        me.text(
            subtitle,
            style=me.Style(font_size="11px", color=TEXT_MUTED, margin=me.Margin(top=2)),
        )
