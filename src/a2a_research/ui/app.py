"""Mesop application: main page and entry point.

``AppState.session`` is always a :class:`~a2a_research.models.ResearchSession`
so Mesop registers the Pydantic model for serialization.

The submit handler is an async generator: it yields to show loading, drains
progress events from a queue while ``run_workflow_async`` runs as a task.
"""

import logging

import mesop as me

from a2a_research.logging.app_logging import (
    get_logger,
    log_event,
    setup_logging,
)
from a2a_research.ui.app_state import AppState, state_snapshot
from a2a_research.ui.components import PageHeader, PageInstructions
from a2a_research.ui import patches  # noqa: F401 - side effects on import
from a2a_research.ui.page_content import (
    render_query_input_card,
    render_session_body,
)
from a2a_research.ui.renderers import page_shell_style
from a2a_research.ui.session_state import has_results
from a2a_research.ui.submit_handler import on_submit
from a2a_research.ui.query_handlers import on_query_input

# Backward-compatible re-exports for tests that patch these names
from a2a_research.ui.components import (  # noqa: F401
    CardLoading,
    CardTimeline,
)

_on_submit = on_submit  # backward-compatible alias for tests
_on_query_input = on_query_input  # backward-compatible alias for tests

setup_logging()
logger = get_logger("a2a_research.ui.app")
log_event(logger, logging.INFO, "ui.app.imported")


@me.page(path="/", title="A2A Research — Multi-Agent Research System")
def main_page() -> None:
    """Render the main application page."""
    state: AppState = me.state(AppState)
    log_event(
        logger,
        logging.INFO,
        "ui.main_page.render.start",
        state=state_snapshot(state),
    )

    try:
        with me.box(style=page_shell_style(state.loading)):
            log_event(
                logger,
                logging.DEBUG,
                "ui.component.render",
                component="PageHeader",
            )
            PageHeader()
            if not has_results(state.session):
                log_event(
                    logger,
                    logging.DEBUG,
                    "ui.component.render",
                    component="PageInstructions",
                )
                PageInstructions()

            render_session_body(state)
            render_query_input_card(state)
    except Exception:
        log_event(
            logger,
            logging.ERROR,
            "ui.main_page.render.failed",
            state=state_snapshot(state),
        )
        logger.exception("main_page render failed")
        raise
    else:
        log_event(
            logger,
            logging.INFO,
            "ui.main_page.render.complete",
            session_id=state.session.id,
        )
