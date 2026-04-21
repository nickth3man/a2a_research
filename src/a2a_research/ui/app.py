"""Mesop application: main page and entry point.

``AppState.session`` is always a :class:`~a2a_research.models.ResearchSession`
so Mesop registers the Pydantic model for serialization.

The submit handler is an async generator: it yields to show loading, drains
progress events from a queue while ``run_workflow_async`` runs as a task.
"""

import logging

import mesop as me

from a2a_research.app_logging import (
    get_logger,
    log_event,
    setup_logging,
)
from a2a_research.ui.app_state import AppState, state_snapshot
from a2a_research.ui.components import (
    CardLoading,
    CardQueryInput,
    CardTimeline,
    PageEmptyState,
    PageHeader,
    PageInstructions,
)
from a2a_research.ui.handlers import on_retry, on_toggle_verbose
from a2a_research.ui import patches  # noqa: F401 - side effects on import
from a2a_research.ui.query_handlers import (
    on_example_a,
    on_example_b,
    on_example_c,
    on_query_input,
)
from a2a_research.ui.renderers import (
    page_shell_style,
    render_error_banner,
    render_results,
)
from a2a_research.ui.session_state import (
    get_session_error,
    has_progress,
    has_results,
)
from a2a_research.ui.submit_handler import on_submit

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
                log_event(
                    logger,
                    logging.INFO,
                    "ui.loading.render",
                    progress_step_label=state.progress_step_label,
                    progress_substep_label=state.current_substep,
                    activity_counts={
                        role: len(lines)
                        for role, lines in getattr(
                            state, "activity_by_role", {}
                        ).items()
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
            else:
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
