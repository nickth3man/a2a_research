"""Page content renderers for the Mesop UI."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from a2a_research.logging.app_logging import get_logger, log_event
from a2a_research.ui.components import (
    CardLoading,
    CardQueryInput,
    CardTimeline,
    PageEmptyState,
)
from a2a_research.ui.handlers import on_retry, on_toggle_verbose
from a2a_research.ui.query_handlers import (
    on_example_a,
    on_example_b,
    on_example_c,
    on_query_input,
)
from a2a_research.ui.renderers import render_error_banner, render_results
from a2a_research.ui.session_state import (
    get_session_error,
    has_progress,
    has_results,
)
from a2a_research.ui.submit_handler import on_submit

if TYPE_CHECKING:
    from a2a_research.ui.app_state import AppState

logger = get_logger("a2a_research.ui.app")


def render_loading_state(state: AppState) -> None:
    """Render the loading card while research is in progress."""
    log_event(
        logger,
        logging.INFO,
        "ui.loading.render",
        progress_step_label=state.progress_step_label,
        progress_substep_label=state.current_substep,
        activity_counts={
            role: len(lines)
            for role, lines in getattr(state, "activity_by_role", {}).items()
        },
    )
    CardLoading(
        progress_step_label=state.progress_step_label,
        session=state.session,
        running_substeps=state.progress_running_substeps,
        activity_by_role=getattr(state, "activity_by_role", {}),
        retry_counts=getattr(state, "retry_counts", {}),
        error_counts=getattr(state, "error_counts", {}),
        show_verbose_prompts=bool(
            getattr(state, "show_verbose_prompts", True)
        ),
        on_toggle_verbose=on_toggle_verbose,
    )


def render_session_body(state: AppState) -> None:
    """Render results, progress timeline, or empty state."""
    session_error = get_session_error(state.session)
    if session_error:
        log_event(
            logger,
            logging.WARNING,
            "ui.component.render",
            component="BannerError",
            error=session_error,
        )
        render_error_banner(session_error, on_retry)

    if state.loading:
        render_loading_state(state)
        return

    if has_results(state.session):
        log_event(
            logger,
            logging.INFO,
            "ui.results.render",
            session_id=state.session.id,
            final_report_chars=len(state.session.final_report),
        )
        render_results(state.session)
    elif has_progress(state.session):
        log_event(
            logger,
            logging.DEBUG,
            "ui.component.render",
            component="CardTimeline",
            state="progress",
        )
        CardTimeline(state.session)
    elif not session_error:
        log_event(
            logger,
            logging.DEBUG,
            "ui.component.render",
            component="PageEmptyState",
        )
        PageEmptyState()


def render_query_input_card(state: AppState) -> None:
    """Render the query input card at the bottom of the page."""
    log_event(
        logger,
        logging.INFO,
        "ui.component.render",
        component="CardQueryInput",
        props={
            "query_text": state.query_text,
            "submit_disabled": state.loading,
            "has_example_handlers": True,
        },
    )
    CardQueryInput(
        on_submit=on_submit,
        on_query_input=on_query_input,
        query_text=state.query_text,
        submit_disabled=state.loading,
        on_example_a=on_example_a,
        on_example_b=on_example_b,
        on_example_c=on_example_c,
    )
