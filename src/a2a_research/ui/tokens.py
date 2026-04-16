"""Design tokens for the Mesop UI (spacing, radii, shadows, typography).

Color functions for domain semantics remain in :mod:`a2a_research.ui.theme`.
This module adds layout constants and re-exports theme helpers for convenience.
"""

from __future__ import annotations

import mesop as me

from a2a_research.ui.theme import status_color, verdict_bg, verdict_color

# Re-export theme functions so UI code can import from one place.
__all__ = [
    # Layout / surfaces
    "AGENT_ROW_BG_IDLE",
    # Progress bar
    "PROGRESS_BAR_HEIGHT",
    "PROGRESS_BAR_BG",
    "PROGRESS_BAR_FILL",
    "SUBSTEP_COLOR",
    "PULSE_BG",
    "AGENT_ROW_BG_RUNNING",
    "BORDER_COLOR",
    "BORDER_WIDTH",
    "CALLOUT_RADIUS",
    "CARD_BACKGROUND",
    "CARD_PADDING",
    "CARD_PADDING_LARGE",
    "CARD_RADIUS",
    "CARD_SHADOW",
    "CLAIM_INNER_RADIUS",
    "CLAIM_PADDING",
    "EMPTY_STATE_BG",
    "EMPTY_STATE_BORDER",
    # Style presets
    "EMPTY_STATE_STYLE",
    "ERROR_BANNER_BG",
    "ERROR_BANNER_BORDER",
    "ERROR_BANNER_STYLE",
    "ERROR_TEXT",
    "FONT_SIZE_BODY",
    "FONT_SIZE_SMALL",
    "FONT_SIZE_SUBTITLE",
    "FONT_SIZE_TINY",
    "HEADER_BORDER_COLOR",
    "HEADER_BORDER_WIDTH",
    "HEADER_STYLE",
    "INSTRUCTIONS_BG",
    "INSTRUCTIONS_BORDER",
    "INSTRUCTIONS_STYLE",
    "LOADING_BG",
    "LOADING_BORDER",
    "LOADING_CARD_STYLE",
    "LOADING_TEXT",
    "MARKDOWN_INNER_RADIUS",
    "PAGE_FONT_FAMILY",
    "PAGE_MAX_WIDTH",
    "PAGE_PADDING",
    "QUERY_CARD_MARGIN_BOTTOM",
    "REPORT_MARKDOWN_BG",
    "SECTION_MARGIN_BOTTOM_MD",
    "SECTION_MARGIN_BOTTOM_SM",
    "SOURCE_ROW_BG",
    "SUBTITLE_MARGIN_BOTTOM",
    "TEXT_MUTED",
    "build_default_border",
    # Theme functions
    "status_color",
    "verdict_bg",
    "verdict_color",
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


def _build_border(color: str) -> me.Border:
    """Build a border with the given color on all sides."""
    side = me.BorderSide(width=BORDER_WIDTH, color=color)
    return me.Border(top=side, right=side, bottom=side, left=side)


# --- Progress bar ---
PROGRESS_BAR_HEIGHT = 8
PROGRESS_BAR_BG = "#e5e7eb"
PROGRESS_BAR_FILL = "#3b82f6"
SUBSTEP_COLOR = "#6b7280"
PULSE_BG = "#eff6ff"


# --- Style Presets for Common Component Patterns ---

# Error banner style preset
ERROR_BANNER_STYLE = me.Style(
    background=ERROR_BANNER_BG,
    border=_build_border(ERROR_BANNER_BORDER),
    border_radius=CALLOUT_RADIUS,
    padding=me.Padding(top=14, right=14, bottom=14, left=14),
    margin=me.Margin(bottom=16),
    display="flex",
    align_items="center",
    gap=12,
)

# Loading card style preset
LOADING_CARD_STYLE = me.Style(
    text_align="center",
    background=LOADING_BG,
    border=_build_border(LOADING_BORDER),
    border_radius=CARD_RADIUS,
    padding=me.Padding(top=32, right=32, bottom=32, left=32),
    margin=me.Margin(bottom=SECTION_MARGIN_BOTTOM_MD),
)

# Header section style preset
HEADER_STYLE = me.Style(
    border=me.Border(
        bottom=me.BorderSide(width=HEADER_BORDER_WIDTH, color=HEADER_BORDER_COLOR),
    ),
    padding=me.Padding(bottom=16),
    margin=me.Margin(bottom=24),
)

# Instructions section style preset
INSTRUCTIONS_STYLE = me.Style(
    background=INSTRUCTIONS_BG,
    border=_build_border(INSTRUCTIONS_BORDER),
    border_radius=8,
    padding=me.Padding(top=14, right=14, bottom=14, left=14),
    margin=me.Margin(bottom=24),
)

# Empty state style preset
EMPTY_STATE_STYLE = me.Style(
    text_align="center",
    background=EMPTY_STATE_BG,
    border=_build_border(EMPTY_STATE_BORDER),
    border_radius=CARD_RADIUS,
    padding=me.Padding(top=48, right=24, bottom=48, left=24),
    margin=me.Margin(bottom=SECTION_MARGIN_BOTTOM_MD),
)
