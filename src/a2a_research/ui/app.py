"""Mesop application: main page, ``AppState``, and event handlers.

``AppState.session`` is a non-optional :class:`~a2a_research.models.ResearchSession`
so Mesop registers the Pydantic model for serialization (optional/union session
fields are skipped and break round-trips).

The submit handler is an **async generator**: it yields to show loading, drains
progress events from a queue while ``run_workflow_async`` runs as a task, then
yields so the completed UI renders.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator, Callable
from contextlib import suppress
from dataclasses import field
from typing import Any, cast

import mesop as me

# Patch Mesop's static file serving to return 404 instead of 500 for missing
# files such as /robots.txt (framework bug on Windows pip installs).
import mesop.server.static_file_serving as _sfs
from flask import Response as _Response

from a2a_research.app_logging import (
    get_logger,
    install_asyncio_exception_logging,
    log_event,
    setup_logging,
)
from a2a_research.models import AgentStatus, ResearchSession
from a2a_research.progress import (
    ProgressEvent,
    ProgressPhase,
    ProgressQueue,
    drain_progress_while_running,
)
from a2a_research.ui.components import (
    BannerError,
    CardLoading,
    CardQueryInput,
    CardTimeline,
    PageEmptyState,
    PageHeader,
    PageInstructions,
    PanelClaims,
    PanelReport,
    PanelSources,
)
from a2a_research.ui.data_access import get_agent_label
from a2a_research.ui.session_state import get_session_error, has_progress, has_results
from a2a_research.ui.tokens import EXAMPLE_QUERIES, PAGE_FONT_FAMILY, PAGE_MAX_WIDTH, PAGE_PADDING

_original_send_file_compressed = _sfs.send_file_compressed


def _patched_send_file_compressed(path: str, disable_gzip_cache: bool) -> Any:
    if not os.path.exists(path):
        return _Response("Not found", status=404)
    return _original_send_file_compressed(path, disable_gzip_cache)


_send_file_compressed_patch: Callable[[str, bool], Any] = _patched_send_file_compressed
cast("Any", _sfs).send_file_compressed = _send_file_compressed_patch

setup_logging()
logger = get_logger(__name__)
log_event(logger, logging.INFO, "ui.app.imported")


@me.stateclass
class AppState:
    query_text: str = ""
    session: ResearchSession = field(default_factory=lambda: ResearchSession())
    loading: bool = False
    progress_granularity: int = 1
    current_substep: str = ""
    progress_pct: float = 0.0
    progress_step_label: str = ""
    progress_running_substeps: list[str] = field(default_factory=list)


def _state_snapshot(state: AppState) -> dict[str, object]:
    return {
        "query_text": state.query_text,
        "loading": state.loading,
        "progress_granularity": state.progress_granularity,
        "progress_pct": round(state.progress_pct, 3),
        "progress_step_label": state.progress_step_label,
        "current_substep": state.current_substep,
        "running_substeps": list(state.progress_running_substeps),
        "session": {
            "id": state.session.id,
            "query": state.session.query,
            "roles": [role.value for role in state.session.roles],
            "agent_statuses": {
                role.value: result.status.value
                for role, result in state.session.agent_results.items()
            },
            "final_report_chars": len(state.session.final_report),
            "error": state.session.error,
        },
    }


@me.page(path="/", title="A2A Research \u2014 Multi-Agent Research System")
def main_page() -> None:
    state: AppState = me.state(AppState)
    log_event(logger, logging.INFO, "ui.main_page.render.start", state=_state_snapshot(state))

    try:
        with me.box(style=_page_shell_style(state.loading)):
            log_event(logger, logging.DEBUG, "ui.component.render", component="PageHeader")
            PageHeader()
            if not has_results(state.session):
                log_event(
                    logger, logging.DEBUG, "ui.component.render", component="PageInstructions"
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
                _render_error_banner(session_error)

            if state.loading:
                log_event(
                    logger,
                    logging.INFO,
                    "ui.loading.render",
                    progress_pct=state.progress_pct,
                    progress_step_label=state.progress_step_label,
                    progress_substep_label=state.current_substep,
                )
                CardLoading(
                    progress_pct=state.progress_pct,
                    progress_step_label=state.progress_step_label,
                    progress_substep_label=state.current_substep,
                    session=state.session,
                    granularity=state.progress_granularity,
                    running_substeps=state.progress_running_substeps,
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
                    _render_results(state.session)
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
                        logger, logging.DEBUG, "ui.component.render", component="PageEmptyState"
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
                    "progress_granularity": state.progress_granularity,
                    "has_example_handlers": True,
                },
            )
            CardQueryInput(
                on_submit=_on_submit,
                on_query_input=_on_query_input,
                query_text=state.query_text,
                submit_disabled=state.loading,
                progress_granularity=state.progress_granularity,
                on_granularity_agent=_on_granularity_agent,
                on_granularity_substep=_on_granularity_substep,
                on_granularity_detail=_on_granularity_detail,
                on_example_a=_on_example_a,
                on_example_b=_on_example_b,
                on_example_c=_on_example_c,
            )
    except Exception:
        log_event(
            logger,
            logging.ERROR,
            "ui.main_page.render.failed",
            state=_state_snapshot(state),
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


def _page_shell_style(loading: bool) -> me.Style:
    return me.Style(
        max_width=PAGE_MAX_WIDTH,
        margin=me.Margin(left="auto", right="auto"),
        padding=PAGE_PADDING,
        font_family=PAGE_FONT_FAMILY,
        background="rgba(239, 246, 255, 0.45)" if loading else None,
        border_radius=14 if loading else None,
        box_shadow="0 0 0 4px rgba(219, 234, 254, 0.65)" if loading else None,
        opacity=0.98 if loading else 1.0,
        transition="background 180ms ease, box-shadow 180ms ease, opacity 180ms ease",
    )


def _render_error_banner(error: str) -> None:
    BannerError(error, on_retry=_on_retry)


def _progress_fraction(evt: ProgressEvent) -> float:
    total = max(evt.total_steps, 1)
    if evt.phase in (ProgressPhase.STEP_COMPLETED, ProgressPhase.STEP_FAILED):
        return min(1.0, (evt.step_index + 1) / total)
    if evt.phase == ProgressPhase.STEP_STARTED:
        return min(1.0, evt.step_index / total)
    denom = max(evt.substep_total, 1)
    return min(1.0, (evt.step_index + evt.substep_index / denom) / total)


def _format_substep_line(evt: ProgressEvent, granularity: int) -> str:
    if evt.detail and granularity >= 3:
        return f"{evt.substep_label} ({evt.detail})"
    return evt.substep_label


def _handle_progress_event(state: AppState, evt: ProgressEvent) -> None:
    log_event(
        logger,
        logging.INFO,
        "ui.progress.event",
        role=evt.role,
        phase=evt.phase,
        step_index=evt.step_index,
        total_steps=evt.total_steps,
        substep_index=evt.substep_index,
        substep_total=evt.substep_total,
        substep_label=evt.substep_label,
        detail=evt.detail,
    )
    state.progress_pct = _progress_fraction(evt)
    granularity = state.progress_granularity
    label = _format_substep_line(evt, granularity)
    state.current_substep = label

    agent_label = get_agent_label(evt.role)
    state.progress_step_label = f"Step {evt.step_index + 1} of {evt.total_steps} — {agent_label}"

    if evt.phase == ProgressPhase.STEP_STARTED:
        state.progress_running_substeps = []
    elif evt.phase == ProgressPhase.STEP_SUBSTEP and granularity >= 2:
        state.progress_running_substeps = [*state.progress_running_substeps, label]

    state.session.ensure_agent_results()
    result = state.session.agent_results[evt.role]
    if evt.phase == ProgressPhase.STEP_STARTED or evt.phase == ProgressPhase.STEP_SUBSTEP:
        state.session.agent_results[evt.role] = result.model_copy(
            update={"status": AgentStatus.RUNNING, "message": label}
        )
    elif evt.phase == ProgressPhase.STEP_COMPLETED:
        state.session.agent_results[evt.role] = result.model_copy(
            update={"status": AgentStatus.COMPLETED, "message": label}
        )
    elif evt.phase == ProgressPhase.STEP_FAILED:
        state.session.agent_results[evt.role] = result.model_copy(
            update={"status": AgentStatus.FAILED, "message": label}
        )


def _render_results(session: ResearchSession) -> None:
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


def _on_query_input(e: me.InputEvent) -> None:
    state: AppState = me.state(AppState)
    log_event(
        logger,
        logging.INFO,
        "ui.query.changed",
        length=len(e.value),
        value=e.value,
        previous_value=state.query_text,
    )
    state.query_text = e.value


def _set_example_query(query: str) -> None:
    state: AppState = me.state(AppState)
    log_event(
        logger,
        logging.INFO,
        "ui.query.example_selected",
        query=query,
        previous_query=state.query_text,
    )
    state.query_text = query
    state.session = ResearchSession(query=query)


def _on_example_a(_e: me.ClickEvent) -> None:
    _set_example_query(EXAMPLE_QUERIES[0])


def _on_example_b(_e: me.ClickEvent) -> None:
    _set_example_query(EXAMPLE_QUERIES[1])


def _on_example_c(_e: me.ClickEvent) -> None:
    _set_example_query(EXAMPLE_QUERIES[2])


def _on_granularity_agent(_e: me.ClickEvent) -> None:
    log_event(logger, logging.INFO, "ui.granularity.changed", granularity="agent")
    me.state(AppState).progress_granularity = 1


def _on_granularity_substep(_e: me.ClickEvent) -> None:
    log_event(logger, logging.INFO, "ui.granularity.changed", granularity="substep")
    me.state(AppState).progress_granularity = 2


def _on_granularity_detail(_e: me.ClickEvent) -> None:
    log_event(logger, logging.INFO, "ui.granularity.changed", granularity="detail")
    me.state(AppState).progress_granularity = 3


async def _on_submit(e: me.ClickEvent) -> AsyncGenerator[None, None]:
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
        state=_state_snapshot(state),
    )

    if not query_text:
        state.session = ResearchSession(
            query="",
            error="Enter a research query before running the pipeline.",
        )
        log_event(
            logger, logging.WARNING, "ui.submit.blocked.empty_query", state=_state_snapshot(state)
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
    state.progress_pct = 0.05
    state.current_substep = ""
    state.progress_step_label = "Starting pipeline\u2026"
    state.progress_running_substeps = []
    log_event(
        logger,
        logging.INFO,
        "ui.submit.started",
        query=query_text,
        session_id=state.session.id,
        granularity=state.progress_granularity,
    )
    yield

    from a2a_research.workflow import run_workflow_async

    wf_task: asyncio.Task[ResearchSession] | None = None
    try:
        queue: ProgressQueue = asyncio.Queue()
        wf_task = asyncio.create_task(
            run_workflow_async(
                query_text,
                progress_queue=queue,
                granularity=state.progress_granularity,
            )
        )
        async for evt in drain_progress_while_running(queue, wf_task):
            _handle_progress_event(state, evt)
            yield

        state.session = wf_task.result()
        if state.session.error:
            state.progress_pct = 0.0
            log_event(
                logger,
                logging.WARNING,
                "ui.submit.completed.with_error",
                session_id=state.session.id,
                error=state.session.error,
                final_report_chars=len(state.session.final_report),
            )
        else:
            state.progress_pct = 1.0
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
        state.session.error = "Live update stream was interrupted. Please retry."
        state.progress_pct = 0.0
        log_event(
            logger,
            logging.WARNING,
            "ui.submit.cancelled",
            query=query_text,
            session_id=state.session.id,
            state=_state_snapshot(state),
        )
    except Exception as exc:
        state.session.error = str(exc)
        state.progress_pct = 0.0
        log_event(
            logger,
            logging.ERROR,
            "ui.submit.failed",
            query=query_text,
            session_id=state.session.id,
            error=str(exc),
            state=_state_snapshot(state),
        )
        logger.exception("UI submit failed query=%r", query_text)
    finally:
        log_event(
            logger,
            logging.INFO,
            "ui.submit.cleanup",
            session_id=state.session.id,
            state_before_cleanup=_state_snapshot(state),
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


async def _on_retry(e: me.ClickEvent) -> AsyncGenerator[None, None]:
    async for _ in _on_submit(e):
        yield
