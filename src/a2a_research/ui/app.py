"""Mesop application: main page, ``AppState``, and event handlers.

``AppState.session`` is a non-optional :class:`~a2a_research.models.ResearchSession`
so Mesop registers the Pydantic model for serialization (optional/union session
fields are skipped and break round-trips).

The submit handler is an **async generator**: it yields to show loading, drains
progress events from a queue while ``run_workflow_async`` runs as a task, then
yields so the completed UI renders.
"""

import asyncio
from collections.abc import AsyncGenerator

import mesop as me

from a2a_research.app_logging import get_logger, setup_logging
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
from a2a_research.ui.state import AppState
from a2a_research.ui.tokens import PAGE_FONT_FAMILY, PAGE_MAX_WIDTH, PAGE_PADDING

setup_logging()
logger = get_logger(__name__)


@me.page(path="/", title="A2A Research \u2014 Multi-Agent Research System")
def main_page() -> None:
    state: AppState = me.state(AppState)

    with me.box(
        style=me.Style(
            max_width=PAGE_MAX_WIDTH,
            margin=me.Margin(left="auto", right="auto"),
            padding=PAGE_PADDING,
            font_family=PAGE_FONT_FAMILY,
        )
    ):
        PageHeader()
        PageInstructions()

        session_error = get_session_error(state.session)
        if session_error:
            BannerError(session_error)

        if state.loading:
            CardLoading(
                progress_pct=state.progress_pct,
                progress_step_label=state.progress_step_label,
                progress_substep_label=state.current_substep,
                session=state.session,
                granularity=state.progress_granularity,
                running_substeps=state.progress_running_substeps,
            )
            CardTimeline(state.session)
        else:
            if has_results(state.session):
                _render_results(state.session)
            elif has_progress(state.session):
                CardTimeline(state.session)
            else:
                PageEmptyState()

        CardQueryInput(
            on_submit=_on_submit,
            on_query_input=_on_query_input,
            submit_disabled=int(state.loading),
            progress_granularity=state.progress_granularity,
            on_granularity_agent=_on_granularity_agent,
            on_granularity_substep=_on_granularity_substep,
            on_granularity_detail=_on_granularity_detail,
        )


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
    CardTimeline(session)
    PanelClaims(session)
    PanelSources(session)
    PanelReport(session)


def _on_query_input(e: me.InputEvent) -> None:
    state: AppState = me.state(AppState)
    state.query_text = e.value


def _on_granularity_agent(_e: me.ClickEvent) -> None:
    me.state(AppState).progress_granularity = 1


def _on_granularity_substep(_e: me.ClickEvent) -> None:
    me.state(AppState).progress_granularity = 2


def _on_granularity_detail(_e: me.ClickEvent) -> None:
    me.state(AppState).progress_granularity = 3


async def _on_submit(e: me.ClickEvent) -> AsyncGenerator[None, None]:
    """Run research on click using Mesop's async-generator loading pattern."""
    state: AppState = me.state(AppState)
    query_text = state.query_text.strip()

    if not query_text:
        state.session = ResearchSession(
            query=query_text,
            error="Enter a research query before running the pipeline.",
        )
        yield
        return

    if state.loading:
        return

    state.loading = True
    state.session = ResearchSession(query=query_text)
    state.session.ensure_agent_results()
    state.progress_pct = 0.0
    state.current_substep = "Starting pipeline\u2026"
    state.progress_step_label = "Preparing\u2026"
    state.progress_running_substeps = []
    logger.info("UI submit query=%r session_id=%s", query_text, state.session.id)
    yield

    try:
        from a2a_research.workflow import run_workflow_async

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
        state.progress_pct = 1.0
        logger.info(
            "UI submit completed session_id=%s final_report_chars=%s",
            state.session.id,
            len(state.session.final_report),
        )
    except Exception as exc:
        state.session.error = str(exc)
        logger.exception("UI submit failed query=%r", query_text)
    finally:
        state.loading = False
        state.current_substep = ""
        state.progress_step_label = ""
        state.progress_running_substeps = []

    yield
