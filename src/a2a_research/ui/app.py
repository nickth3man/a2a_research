"""Mesop application: main page, ``AppState``, and event handlers.

``AppState.session`` is always a :class:`~a2a_research.models.ResearchSession`
so Mesop registers the Pydantic model for serialization (union-typed session
fields are skipped and break round-trips).

The submit handler is an **async generator**: it yields to show loading, drains
progress events from a queue while ``run_workflow_async`` runs as a task, then
yields so the completed UI renders.
"""

import asyncio
import dataclasses
import logging
import os
import sys
from collections.abc import AsyncGenerator, Callable
from contextlib import suppress
from typing import Any, cast

import mesop as me

# Conditionally patch Mesop's static file serving on Windows to return 404
# instead of 500 for missing files such as /robots.txt (framework bug on Windows).
if sys.platform == "win32":
    import mesop.server.static_file_serving as _sfs
    from flask import Response as _Response

    _original_send_file_compressed = _sfs.send_file_compressed

    def _patched_send_file_compressed(
        path: str, disable_gzip_cache: bool
    ) -> Any:
        if not os.path.exists(path):
            return _Response("Not found", status=404)
        return _original_send_file_compressed(path, disable_gzip_cache)

    _send_file_compressed_patch: Callable[[str, bool], Any] = (
        _patched_send_file_compressed
    )
    cast("Any", _sfs).send_file_compressed = _send_file_compressed_patch

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
from a2a_research.ui.session_state import (
    get_session_error,
    has_progress,
    has_results,
)
from a2a_research.ui.tokens import (
    EXAMPLE_QUERIES,
    PAGE_FONT_FAMILY,
    PAGE_MAX_WIDTH,
    PAGE_PADDING,
)

setup_logging()
# Mesop loads this module with a filesystem-derived ``__name__`` on Windows; use a
# stable logger so events stay under ``a2a_research.ui`` and dedupe in log viewers.
logger = get_logger("a2a_research.ui.app")
log_event(logger, logging.INFO, "ui.app.imported")


@me.stateclass
class AppState:
    query_text: str = ""
    session: ResearchSession = dataclasses.field(
        default_factory=ResearchSession
    )
    loading: bool = False
    current_substep: str = ""
    progress_step_label: str = ""
    progress_running_substeps: list[str] = dataclasses.field(
        default_factory=list
    )
    # Per-role activity feed: role label → list of "HH:MM:SS  text" lines, appended
    # on every progress event. Drives the live per-agent activity panel that
    # replaced the coarse percentage bar.
    activity_by_role: dict[str, list[str]] = dataclasses.field(
        default_factory=dict
    )
    show_verbose_prompts: bool = True
    retry_counts: dict[str, int] = dataclasses.field(default_factory=dict)
    error_counts: dict[str, int] = dataclasses.field(default_factory=dict)


def _state_snapshot(state: AppState) -> dict[str, object]:
    activity_by_role = getattr(state, "activity_by_role", {})
    return {
        "query_text": state.query_text,
        "loading": state.loading,
        "progress_step_label": state.progress_step_label,
        "current_substep": state.current_substep,
        "running_substeps": list(state.progress_running_substeps),
        "activity_counts": {
            role: len(lines) for role, lines in activity_by_role.items()
        },
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
    log_event(
        logger,
        logging.INFO,
        "ui.main_page.render.start",
        state=_state_snapshot(state),
    )

    try:
        with me.box(style=_page_shell_style(state.loading)):
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
                _render_error_banner(session_error)

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
                    on_toggle_verbose=_on_toggle_verbose,
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
                on_submit=_on_submit,
                on_query_input=_on_query_input,
                query_text=state.query_text,
                submit_disabled=state.loading,
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


_ACTIVITY_MAX_LINES_PER_ROLE = 80


def _initialize_progress_state(state: AppState) -> None:
    """Reset progress-related UI state for a fresh run."""
    state.progress_running_substeps = []
    state.current_substep = ""
    state.progress_step_label = "Running the 5-agent research pipeline\u2026"
    state.activity_by_role = {}
    state.retry_counts = {}
    state.error_counts = {}


def _append_activity(
    state: AppState, role_label: str, icon: str, text: str
) -> None:
    from datetime import datetime

    ts = datetime.now().strftime("%H:%M:%S")
    line = f"{ts}  {icon}  {text}"
    lines = state.activity_by_role.get(role_label)
    if lines is None:
        lines = []
        state.activity_by_role[role_label] = lines
    lines.append(line)
    if len(lines) > _ACTIVITY_MAX_LINES_PER_ROLE:
        del lines[: len(lines) - _ACTIVITY_MAX_LINES_PER_ROLE]


def _role_label(role: object) -> str:
    value = getattr(role, "value", str(role))
    return str(value).replace("_", " ").title()


def _format_progress_text(event: ProgressEvent) -> str:
    label = event.substep_label.replace("_", " ").replace(":", ": ")
    parts = [label]
    if event.substep_total and event.substep_total > 1:
        parts.append(f"[{event.substep_index}/{event.substep_total}]")
    if event.detail:
        parts.append(f"— {event.detail}")
    if event.elapsed_ms is not None:
        parts.append(f"({event.elapsed_ms:.0f}ms)")
    return " ".join(parts)


def _apply_progress_event(state: AppState, event: ProgressEvent) -> None:
    state.session.ensure_agent_results()
    role_label = _role_label(event.role)
    display = _format_progress_text(event)
    step_result = state.session.agent_results[event.role]

    if event.phase == ProgressPhase.STEP_STARTED:
        state.session.agent_results[event.role] = step_result.model_copy(
            update={"status": AgentStatus.RUNNING, "message": display}
        )
        if role_label not in state.progress_running_substeps:
            state.progress_running_substeps.append(role_label)
        state.progress_step_label = f"{role_label}…"
        _append_activity(state, role_label, "▶", f"started — {display}")
        return

    if event.phase == ProgressPhase.STEP_SUBSTEP:
        state.session.agent_results[event.role] = step_result.model_copy(
            update={"status": AgentStatus.RUNNING, "message": display}
        )
        state.current_substep = display
        state.progress_step_label = f"{role_label}…"
        _append_activity(state, role_label, "·", display)
        if event.substep_label == "rate_limit":
            state.retry_counts[role_label] = (
                state.retry_counts.get(role_label, 0) + 1
            )
        if (
            event.substep_label == "tool_call"
            and "status=error" in event.detail.lower()
        ):
            state.error_counts[role_label] = (
                state.error_counts.get(role_label, 0) + 1
            )
        return

    if event.phase == ProgressPhase.STEP_COMPLETED:
        state.session.agent_results[event.role] = step_result.model_copy(
            update={"status": AgentStatus.COMPLETED, "message": display}
        )
        state.progress_running_substeps = [
            item
            for item in state.progress_running_substeps
            if item != role_label
        ]
        state.progress_step_label = f"{role_label} completed"
        state.current_substep = ""
        _append_activity(state, role_label, "✓", f"completed — {display}")
        return

    if event.phase == ProgressPhase.STEP_FAILED:
        state.session.agent_results[event.role] = step_result.model_copy(
            update={"status": AgentStatus.FAILED, "message": display}
        )
        state.progress_running_substeps = [
            item
            for item in state.progress_running_substeps
            if item != role_label
        ]
        state.progress_step_label = f"{role_label} failed"
        state.current_substep = display
        _append_activity(state, role_label, "✗", f"failed — {display}")
        state.error_counts[role_label] = (
            state.error_counts.get(role_label, 0) + 1
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
            logger,
            logging.WARNING,
            "ui.submit.blocked.empty_query",
            state=_state_snapshot(state),
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
    _initialize_progress_state(state)
    state.progress_step_label = "Starting pipeline\u2026"
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
        progress_queue: ProgressQueue = asyncio.Queue()
        wf_task = asyncio.create_task(
            run_research_async(query_text, progress_queue=progress_queue)
        )
        async for event in drain_progress_while_running(
            progress_queue, wf_task
        ):
            _apply_progress_event(state, event)
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
            state=_state_snapshot(state),
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


def _on_toggle_verbose(e: me.ClickEvent) -> None:
    state: AppState = me.state(AppState)
    state.show_verbose_prompts = not state.show_verbose_prompts


async def _on_retry(e: me.ClickEvent) -> AsyncGenerator[None, None]:
    async for _ in _on_submit(e):
        yield
