"""Main submit handler for running the research pipeline."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import suppress

import mesop as me

from a2a_research.logging.app_logging import (
    get_logger,
    install_asyncio_exception_logging,
    log_event,
)
from a2a_research.models import ResearchSession
from a2a_research.progress import (
    drain_progress_while_running,
)
from a2a_research.ui.session_state import get_session_error

from .app_state import AppState, state_snapshot
from .progress import apply_progress_event, initialize_progress_state

logger = get_logger("a2a_research.ui.handlers")


async def on_submit(e: me.ClickEvent) -> AsyncGenerator[None, None]:
    """Run research on click using Mesop's async-generator loading pattern."""
    install_asyncio_exception_logging()
    state: AppState = me.state(AppState)
    query_text = state.query_text.strip() or state.session.query.strip()
    log_event(
        logger,
        logging.INFO,
        "ui.submit.clicked",
        query=query_text,
        event_type=type(e).__name__,
        state=state_snapshot(state),
    )

    if not query_text:
        state.session = ResearchSession(
            query="",
            error="Enter a research query before running the pipeline.",
        )
        log_event(
            logger,
            logging.WARNING,
            "ui.submit.blocked.empty_query",
            state=state_snapshot(state),
        )
        yield
        return

    if state.loading:
        log_event(
            logger,
            logging.WARNING,
            "ui.submit.ignored.already_loading",
            session_id=state.session.id,
        )
        return

    state.loading = True
    state.session = ResearchSession(query=query_text)
    state.session.ensure_agent_results()
    initialize_progress_state(state)
    state.progress_step_label = "Starting pipeline…"
    log_event(
        logger,
        logging.INFO,
        "ui.submit.started",
        query=query_text,
        session_id=state.session.id,
    )
    yield

    from a2a_research.workflow import run_research_async

    wf_task: asyncio.Task[ResearchSession] | None = None
    try:
        progress_queue: asyncio.Queue = asyncio.Queue()
        wf_task = asyncio.create_task(
            run_research_async(query_text, progress_queue=progress_queue)
        )
        async for event in drain_progress_while_running(
            progress_queue, wf_task
        ):
            apply_progress_event(state, event)
            yield

        state.session = wf_task.result()
        if state.session.error:
            log_event(
                logger,
                logging.WARNING,
                "ui.submit.completed.with_error",
                session_id=state.session.id,
                error=state.session.error,
                final_report_chars=len(state.session.final_report),
            )
        else:
            log_event(
                logger,
                logging.INFO,
                "ui.submit.completed",
                session_id=state.session.id,
                final_report_chars=len(state.session.final_report),
                agent_statuses={
                    role.value: result.status.value
                    for role, result in state.session.agent_results.items()
                },
            )
    except asyncio.CancelledError:
        state.session.error = (
            "Live update stream was interrupted. Please retry."
        )
        log_event(
            logger,
            logging.WARNING,
            "ui.submit.cancelled",
            query=query_text,
            session_id=state.session.id,
            state=state_snapshot(state),
        )
    except Exception as exc:
        state.session.error = str(exc)
        log_event(
            logger,
            logging.ERROR,
            "ui.submit.failed",
            query=query_text,
            session_id=state.session.id,
            error=str(exc),
            state=state_snapshot(state),
        )
        logger.exception("UI submit failed query=%r", query_text)
    finally:
        log_event(
            logger,
            logging.INFO,
            "ui.submit.cleanup",
            session_id=state.session.id,
            state_before_cleanup=state_snapshot(state),
        )
        if wf_task is not None and not wf_task.done():
            wf_task.cancel()
            with suppress(asyncio.CancelledError):
                await wf_task
        state.loading = False
        state.current_substep = ""
        state.progress_step_label = ""
        state.progress_running_substeps = []

    yield
