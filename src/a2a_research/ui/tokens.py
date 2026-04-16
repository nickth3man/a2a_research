"""Design tokens for the Mesop UI (spacing, radii, shadows, typography).

Color functions for domain semantics remain in :mod:`a2a_research.ui.theme`.
This module adds layout constants and re-exports theme helpers for convenience.
"""

from __future__ import annotations

import mesop as me

from a2a_research.ui.theme import status_color, verdict_bg, verdict_color

# Re-export theme functions so UI code can import from one place.
__all__ = [
    "status_color",
    "verdict_bg",
    "verdict_color",
    # layout / surfaces
    "BORDER_COLOR",
    "BORDER_WIDTH",
    "CARD_BACKGROUND",
    "CARD_RADIUS",
    "CARD_SHADOW",
    "CARD_PADDING",
    "CARD_PADDING_LARGE",
    "PAGE_MAX_WIDTH",
    "PAGE_PADDING",
    "PAGE_FONT_FAMILY",
    "TEXT_MUTED",
    "FONT_SIZE_BODY",
    "FONT_SIZE_SMALL",
    "FONT_SIZE_TINY",
    "FONT_SIZE_SUBTITLE",
    "SUBTITLE_MARGIN_BOTTOM",
    "SECTION_MARGIN_BOTTOM_SM",
    "SECTION_MARGIN_BOTTOM_MD",
    "HEADER_BORDER_COLOR",
    "HEADER_BORDER_WIDTH",
    "INSTRUCTIONS_BG",
    "INSTRUCTIONS_BORDER",
    "EMPTY_STATE_BG",
    "EMPTY_STATE_BORDER",
    "AGENT_ROW_BG_IDLE",
    "AGENT_ROW_BG_RUNNING",
    "SOURCE_ROW_BG",
    "REPORT_MARKDOWN_BG",
    "ERROR_BANNER_BG",
    "ERROR_BANNER_BORDER",
    "ERROR_TEXT",
    "LOADING_BG",
    "LOADING_BORDER",
    "LOADING_TEXT",
    "CLAIM_INNER_RADIUS",
    "CALLOUT_RADIUS",
    "CLAIM_PADDING",
    "MARKDOWN_INNER_RADIUS",
    "QUERY_CARD_MARGIN_BOTTOM",
    "build_default_border",
]

# --- Core card surface ---
BORDER_COLOR = "#e5e7eb"
BORDER_WIDTH = 1
CARD_BACKGROUND = "#fff"
CARD_RADIUS = 10
CARD_SHADOW = "0 1px 3px rgba(0,0,0,0.08)"
CARD_PADDING = me.Padding(top=16, right=16, bottom=16, left=16)
CARD_PADDING_LARGE = me.Padding(top=20, right=20, bottom=20, left=20)

# --- Page shell ---
PAGE_MAX_WIDTH = 900
PAGE_PADDING = me.Padding(left=16, right=16, top=24, bottom=24)
PAGE_FONT_FAMILY = "system-ui, -apple-system, sans-serif"

# --- Typography ---
TEXT_MUTED = "#6b7280"
FONT_SIZE_BODY = "14px"
FONT_SIZE_SMALL = "12px"
FONT_SIZE_TINY = "11px"
FONT_SIZE_SUBTITLE = "15px"
SUBTITLE_MARGIN_BOTTOM = me.Margin(bottom=12)

# --- Section spacing (outer wrapper before card inner) ---
SECTION_MARGIN_BOTTOM_SM = 16
SECTION_MARGIN_BOTTOM_MD = 20

# --- Header / instructions / empty (page_sections) ---
HEADER_BORDER_COLOR = BORDER_COLOR
HEADER_BORDER_WIDTH = 2
INSTRUCTIONS_BG = "#eff6ff"
INSTRUCTIONS_BORDER = "#bfdbfe"
EMPTY_STATE_BG = "#f9fafb"
EMPTY_STATE_BORDER = "#d1d5db"

# --- Agent timeline rows ---
AGENT_ROW_BG_IDLE = "#f9fafb"
AGENT_ROW_BG_RUNNING = "#fffbeb"

# --- Sources list ---
SOURCE_ROW_BG = "#f3f4f6"

# --- Report markdown block ---
REPORT_MARKDOWN_BG = "#fafafa"

# --- Banners ---
ERROR_BANNER_BG = "#fef2f2"
ERROR_BANNER_BORDER = "#fecaca"
ERROR_TEXT = "#dc2626"
LOADING_BG = "#fffbeb"
LOADING_BORDER = "#fde68a"
LOADING_TEXT = "#92400e"

# --- Claims ---
CLAIM_INNER_RADIUS = 8
CALLOUT_RADIUS = 8
CLAIM_PADDING = me.Padding(top=14, right=14, bottom=14, left=14)
MARKDOWN_INNER_RADIUS = 6

QUERY_CARD_MARGIN_BOTTOM = 16


def build_default_border() -> me.Border:
    """Standard1px border on all sides using :data:`BORDER_COLOR`."""
    side = me.BorderSide(width=BORDER_WIDTH, color=BORDER_COLOR)
    return me.Border(top=side, right=side, bottom=side, left=side)
