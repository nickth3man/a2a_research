"""Rendering helpers for the main page."""

import logging

import mesop as me

from a2a_research.logging.app_logging import get_logger, log_event
from a2a_research.models import ResearchSession
from a2a_research.ui.components import (
    BannerError,
    CardTimeline,
    PanelClaims,
    PanelReport,
    PanelSources,
)
from a2a_research.ui.tokens import (
    PAGE_FONT_FAMILY,
    PAGE_MAX_WIDTH,
    PAGE_PADDING,
)

from .app_state import AppState

logger = get_logger("a2a_research.ui.renderers")


def page_shell_style(loading: bool) -> me.Style:
    """Return the main page container style based on loading state."""
    return me.Style(
        max_width=PAGE_MAX_WIDTH,
        margin=me.Margin(left="auto", right="auto"),
        padding=PAGE_PADDING,
        font_family=PAGE_FONT_FAMILY,
        background="rgba(239, 246, 255, 0.45)" if loading else None,
        border_radius=14 if loading else None,
        box_shadow=(
            "0 0 0 4px rgba(219, 234, 254, 0.65)" if loading else None
        ),
        opacity=0.98 if loading else 1.0,
        transition=(
            "background 180ms ease, box-shadow 180ms ease, opacity 180ms ease"
        ),
    )


def render_error_banner(error: str, on_retry: callable) -> None:
    """Render the error banner with optional retry button."""
    BannerError(error, on_retry=on_retry)


def render_results(session: ResearchSession) -> None:
    """Render the results panels (report, claims, sources, timeline)."""
    log_event(
        logger,
        logging.INFO,
        "ui.results.panels.render",
        session_id=session.id,
        agent_count=len(session.agent_results),
        report_chars=len(session.final_report),
    )
    PanelReport(session)
    PanelClaims(session)
    PanelSources(session)
    CardTimeline(session)
