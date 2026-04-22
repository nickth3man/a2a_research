"""Layout design tokens for the Mesop UI (spacing, radii, padding, shadows)."""

from __future__ import annotations

import mesop as me

__all__ = [
    "BORDER_WIDTH",
    "CALLOUT_RADIUS",
    "CARD_PADDING",
    "CARD_PADDING_LARGE",
    "CARD_RADIUS",
    "CARD_SHADOW",
    "CHIP_RADIUS",
    "CLAIM_INNER_RADIUS",
    "CLAIM_PADDING",
    "EMPTY_STATE_ICON_SIZE",
    "FONT_SIZE_BODY",
    "FONT_SIZE_SMALL",
    "FONT_SIZE_SUBTITLE",
    "FONT_SIZE_TINY",
    "HEADER_BORDER_WIDTH",
    "LOADING_DOT_SIZE",
    "MARKDOWN_INNER_RADIUS",
    "PAGE_FONT_FAMILY",
    "PAGE_MAX_WIDTH",
    "PAGE_PADDING",
    "PROGRESS_BAR_HEIGHT",
    "QUERY_CARD_MARGIN_BOTTOM",
    "SECTION_MARGIN_BOTTOM_MD",
    "SECTION_MARGIN_BOTTOM_SM",
    "SUBMIT_BUTTON_PADDING",
    "SUBTITLE_MARGIN_BOTTOM",
    "build_default_border",
]

# --- Core card surface ---
BORDER_WIDTH = 1
CARD_RADIUS = 10
CARD_SHADOW = "0 1px 3px rgba(0,0,0,0.08)"
CARD_PADDING = me.Padding(top=16, right=16, bottom=16, left=16)
CARD_PADDING_LARGE = me.Padding(top=20, right=20, bottom=20, left=20)

# --- Page shell ---
PAGE_MAX_WIDTH = 900
PAGE_PADDING = me.Padding(left=16, right=16, top=24, bottom=24)
PAGE_FONT_FAMILY = "system-ui, -apple-system, sans-serif"

# --- Typography ---
FONT_SIZE_BODY = "14px"
FONT_SIZE_SMALL = "12px"
FONT_SIZE_TINY = "11px"
FONT_SIZE_SUBTITLE = "15px"
SUBTITLE_MARGIN_BOTTOM = me.Margin(bottom=12)

# --- Section spacing ---
SECTION_MARGIN_BOTTOM_SM = 16
SECTION_MARGIN_BOTTOM_MD = 20

# --- Header ---
HEADER_BORDER_WIDTH = 2

# --- Chips / buttons ---
CHIP_RADIUS = 20
SUBMIT_BUTTON_PADDING = me.Padding(top=10, right=24, bottom=10, left=24)

# --- Example / query ---
QUERY_CARD_MARGIN_BOTTOM = 16

# --- Claims ---
CLAIM_INNER_RADIUS = 8
CALLOUT_RADIUS = 8
CLAIM_PADDING = me.Padding(top=14, right=14, bottom=14, left=14)
MARKDOWN_INNER_RADIUS = 6

# --- Empty state ---
EMPTY_STATE_ICON_SIZE = "42px"

# --- Banners ---
LOADING_DOT_SIZE = 16

# --- Progress bar ---
PROGRESS_BAR_HEIGHT = 8

# --- Granularity ---
GRANULARITY_SELECTED_SHADOW = "0 1px 3px rgba(0,0,0,0.15)"


def build_default_border() -> me.Border:
    """Standard 1px border on all sides using :data:`BORDER_COLOR`."""
    from a2a_research.ui.tokens_content import BORDER_COLOR

    side = me.BorderSide(width=BORDER_WIDTH, color=BORDER_COLOR)
    return me.Border(top=side, right=side, bottom=side, left=side)
