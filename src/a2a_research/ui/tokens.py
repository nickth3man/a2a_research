"""Design tokens for the Mesop UI (spacing, radii, shadows, typography).

Color functions for domain semantics remain in :mod:`a2a_research.ui.theme`.
This module adds layout constants and re-exports theme helpers.
"""

from __future__ import annotations

import mesop as me

from a2a_research.ui.theme import (
    STATUS_LABELS,
    status_color,
    verdict_bg,
    verdict_color,
)

__all__ = [
    "AGENT_ROW_BG_IDLE",
    "AGENT_ROW_BG_RUNNING",
    "BORDER_COLOR",
    "BORDER_WIDTH",
    "CALLOUT_RADIUS",
    "CARD_BACKGROUND",
    "CARD_PADDING",
    "CARD_PADDING_LARGE",
    "CARD_RADIUS",
    "CARD_SHADOW",
    "CHIP_BG",
    "CHIP_BORDER",
    "CHIP_RADIUS",
    "CHIP_TEXT_COLOR",
    "CLAIM_INNER_RADIUS",
    "CLAIM_PADDING",
    "EMPTY_STATE_BG",
    "EMPTY_STATE_BORDER",
    "EMPTY_STATE_ICON_BG",
    "EMPTY_STATE_ICON_SIZE",
    "ERROR_BANNER_BG",
    "ERROR_BANNER_BORDER",
    "ERROR_ICON_COLOR",
    "ERROR_TEXT",
    "EVIDENCE_TEXT_COLOR",
    "EXAMPLE_QUERIES",
    "EXAMPLE_QUERY_COLOR",
    "FONT_SIZE_BODY",
    "FONT_SIZE_SMALL",
    "FONT_SIZE_SUBTITLE",
    "FONT_SIZE_TINY",
    "GRANULARITY_GROUP_BG",
    "GRANULARITY_SELECTED_BG",
    "GRANULARITY_SELECTED_SHADOW",
    "HEADER_ACCENT_COLOR",
    "HEADER_BORDER_COLOR",
    "HEADER_BORDER_WIDTH",
    "INSTRUCTIONS_BG",
    "INSTRUCTIONS_BORDER",
    "LOADING_BG",
    "LOADING_BORDER",
    "LOADING_DOT_SIZE",
    "LOADING_TEXT",
    "MARKDOWN_INNER_RADIUS",
    "PAGE_FONT_FAMILY",
    "PAGE_MAX_WIDTH",
    "PAGE_PADDING",
    "PROGRESS_BAR_BG",
    "PROGRESS_BAR_FILL",
    "PROGRESS_BAR_HEIGHT",
    "PULSE_BG",
    "QUERY_CARD_MARGIN_BOTTOM",
    "REPORT_MARKDOWN_BG",
    "SECTION_MARGIN_BOTTOM_MD",
    "SECTION_MARGIN_BOTTOM_SM",
    "SOURCE_ROW_BG",
    "STATUS_LABELS",
    "STEP_CARD_BORDER",
    "SUBMIT_BUTTON_PADDING",
    "SUBSTEP_COLOR",
    "SUBTITLE_MARGIN_BOTTOM",
    "TEXT_MUTED",
    "build_default_border",
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

# --- Section spacing ---
SECTION_MARGIN_BOTTOM_SM = 16
SECTION_MARGIN_BOTTOM_MD = 20

# --- Header / instructions / empty ---
HEADER_ACCENT_COLOR = "#2563eb"
HEADER_BORDER_COLOR = BORDER_COLOR
HEADER_BORDER_WIDTH = 2
HEADER_SUBTITLE_COLOR = "#374151"
INSTRUCTIONS_BG = "#eff6ff"
INSTRUCTIONS_BORDER = "#bfdbfe"
STEP_CARD_BORDER = "#dbeafe"
EMPTY_STATE_BG = "#f9fafb"
EMPTY_STATE_BORDER = "#d1d5db"
EXAMPLE_QUERY_COLOR = "#1d4ed8"
CHIP_BG = "#eff6ff"
CHIP_BORDER = "#bfdbfe"
CHIP_RADIUS = 20
CHIP_TEXT_COLOR = EXAMPLE_QUERY_COLOR
SUBMIT_BUTTON_PADDING = me.Padding(top=10, right=24, bottom=10, left=24)
GRANULARITY_GROUP_BG = "#f3f4f6"
GRANULARITY_SELECTED_BG = "#ffffff"
GRANULARITY_SELECTED_SHADOW = "0 1px 3px rgba(0,0,0,0.15)"

# --- Example queries ---
EXAMPLE_QUERIES: list[str] = [
    (
        "When did the James Webb Space Telescope launch and what is its"
        " primary mirror diameter?"
    ),
    "What are the main differences between the A2A protocol and MCP?",
    (
        "What year was the transformer architecture paper published, and"
        " who are the authors?"
    ),
]

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
ERROR_ICON_COLOR = "#dc2626"
LOADING_BG = "#fffbeb"
LOADING_BORDER = "#fde68a"
LOADING_TEXT = "#92400e"
LOADING_DOT_SIZE = 16

# --- Empty state ---
EMPTY_STATE_ICON_SIZE = "42px"
EMPTY_STATE_ICON_BG = "#eff6ff"

# --- Claims ---
CLAIM_INNER_RADIUS = 8
CALLOUT_RADIUS = 8
CLAIM_PADDING = me.Padding(top=14, right=14, bottom=14, left=14)
MARKDOWN_INNER_RADIUS = 6
EVIDENCE_TEXT_COLOR = "#374151"

QUERY_CARD_MARGIN_BOTTOM = 16

# --- Progress bar ---
PROGRESS_BAR_HEIGHT = 8
PROGRESS_BAR_BG = "#e5e7eb"
PROGRESS_BAR_FILL = "#3b82f6"
SUBSTEP_COLOR = "#6b7280"
PULSE_BG = "#eff6ff"


def build_default_border() -> me.Border:
    """Standard 1px border on all sides using :data:`BORDER_COLOR`."""
    side = me.BorderSide(width=BORDER_WIDTH, color=BORDER_COLOR)
    return me.Border(top=side, right=side, bottom=side, left=side)
