"""Instruction step helpers for page sections."""

from __future__ import annotations

import mesop as me

from a2a_research.ui.tokens import (
    CARD_BACKGROUND,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    HEADER_ACCENT_COLOR,
    STEP_CARD_BORDER,
    TEXT_MUTED,
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
            me.text(
                title,
                style=me.Style(font_size=FONT_SIZE_BODY, font_weight="bold"),
            )
            me.text(
                description,
                style=me.Style(
                    font_size=FONT_SIZE_SMALL,
                    color=TEXT_MUTED,
                    margin=me.Margin(top=4),
                ),
            )


INSTRUCTION_STEPS: list[tuple[str, str, str]] = [
    ("1", "Enter a query", "Start a research session."),
    (
        "2",
        "Sources retrieved",
        "Pull relevant documents from the local corpus.",
    ),
    ("3", "Agents analyze", "Research, verify, and refine claims."),
    ("4", "Report renders", "Review sources, claims, and summary."),
]
