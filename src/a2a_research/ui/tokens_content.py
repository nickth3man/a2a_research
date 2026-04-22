"""Content design tokens for the Mesop UI (colors, labels, example queries)."""

from __future__ import annotations

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
    "CARD_BACKGROUND",
    "CHIP_BG",
    "CHIP_BORDER",
    "CHIP_TEXT_COLOR",
    "EMPTY_STATE_BG",
    "EMPTY_STATE_BORDER",
    "EMPTY_STATE_ICON_BG",
    "ERROR_BANNER_BG",
    "ERROR_BANNER_BORDER",
    "ERROR_ICON_COLOR",
    "ERROR_TEXT",
    "EVIDENCE_TEXT_COLOR",
    "EXAMPLE_QUERIES",
    "EXAMPLE_QUERY_COLOR",
    "GRANULARITY_GROUP_BG",
    "GRANULARITY_SELECTED_BG",
    "HEADER_ACCENT_COLOR",
    "HEADER_BORDER_COLOR",
    "HEADER_SUBTITLE_COLOR",
    "INSTRUCTIONS_BG",
    "INSTRUCTIONS_BORDER",
    "LOADING_BG",
    "LOADING_BORDER",
    "LOADING_TEXT",
    "PROGRESS_BAR_BG",
    "PROGRESS_BAR_FILL",
    "PULSE_BG",
    "REPORT_MARKDOWN_BG",
    "SOURCE_ROW_BG",
    "STATUS_LABELS",
    "STEP_CARD_BORDER",
    "SUBSTEP_COLOR",
    "TEXT_MUTED",
    "status_color",
    "verdict_bg",
    "verdict_color",
]

# --- Core card surface ---
BORDER_COLOR = "#e5e7eb"
CARD_BACKGROUND = "#fff"

# --- Text ---
TEXT_MUTED = "#6b7280"

# --- Header / instructions / empty ---
HEADER_ACCENT_COLOR = "#2563eb"
HEADER_BORDER_COLOR = BORDER_COLOR
HEADER_SUBTITLE_COLOR = "#374151"
INSTRUCTIONS_BG = "#eff6ff"
INSTRUCTIONS_BORDER = "#bfdbfe"
STEP_CARD_BORDER = "#dbeafe"
EMPTY_STATE_BG = "#f9fafb"
EMPTY_STATE_BORDER = "#d1d5db"
EXAMPLE_QUERY_COLOR = "#1d4ed8"
CHIP_BG = "#eff6ff"
CHIP_BORDER = "#bfdbfe"
CHIP_TEXT_COLOR = EXAMPLE_QUERY_COLOR
GRANULARITY_GROUP_BG = "#f3f4f6"
GRANULARITY_SELECTED_BG = "#ffffff"

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

# --- Empty state ---
EMPTY_STATE_ICON_BG = "#eff6ff"

# --- Claims ---
EVIDENCE_TEXT_COLOR = "#374151"
SUBSTEP_COLOR = "#6b7280"
PULSE_BG = "#eff6ff"

# --- Progress bar ---
PROGRESS_BAR_BG = "#e5e7eb"
PROGRESS_BAR_FILL = "#3b82f6"
