"""Shared Mesop layout primitives (card shells, badges) built from design tokens."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

import mesop as me

from a2a_research.ui.tokens import (
    BORDER_WIDTH,
    CARD_BACKGROUND,
    CARD_PADDING,
    CARD_RADIUS,
    CARD_SHADOW,
    FONT_SIZE_TINY,
    build_default_border,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def card_box(*, margin_bottom: int, padding: me.Padding | None = None) -> Iterator[None]:
    """Standard white card: outer margin wrapper + inner elevated surface."""
    pad = padding if padding is not None else CARD_PADDING
    with me.box(style=me.Style(margin=me.Margin(bottom=margin_bottom))), me.box(
        style=me.Style(
            background=CARD_BACKGROUND,
            border_radius=CARD_RADIUS,
            box_shadow=CARD_SHADOW,
            border=build_default_border(),
            padding=pad,
        )
    ):
        yield


def query_input_card_style() -> me.Style:
    """Single-box card used for the query form (margin included on same node)."""
    from a2a_research.ui.tokens import CARD_PADDING_LARGE, QUERY_CARD_MARGIN_BOTTOM

    return me.Style(
        background=CARD_BACKGROUND,
        border_radius=CARD_RADIUS,
        box_shadow=CARD_SHADOW,
        border=build_default_border(),
        padding=CARD_PADDING_LARGE,
        margin=me.Margin(bottom=QUERY_CARD_MARGIN_BOTTOM),
    )


def verdict_badge_text(badge: str, verdict_color: str) -> None:
    """Outlined verdict pill next to claim text."""
    me.text(
        badge,
        style=me.Style(
            color=verdict_color,
            font_size=FONT_SIZE_TINY,
            background="#fff",
            padding=me.Padding(top=2, bottom=2, left=8, right=8),
            border_radius=4,
            border=me.Border(
                top=me.BorderSide(width=BORDER_WIDTH, color=verdict_color),
                right=me.BorderSide(width=BORDER_WIDTH, color=verdict_color),
                bottom=me.BorderSide(width=BORDER_WIDTH, color=verdict_color),
                left=me.BorderSide(width=BORDER_WIDTH, color=verdict_color),
            ),
        ),
    )
