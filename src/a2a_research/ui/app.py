"""Mesop application: main page, ``AppState``, and event handlers.

``AppState.session`` is a non-optional :class:`~a2a_research.models.ResearchSession`
so Mesop registers the Pydantic model for serialization (optional/union session
fields are skipped and break round-trips).

The submit handler is an **async generator**: it yields to show loading, awaits
``run_workflow_async`` on Mesop's event loop (no nested ``asyncio.run``), then yields
again so the completed UI renders.
"""

from collections.abc import AsyncGenerator
from dataclasses import field

import mesop as me

from a2a_research.app_logging import get_logger, setup_logging
from a2a_research.models import ResearchSession
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
from a2a_research.ui.session_state import get_session_error, has_progress, has_results
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
            CardLoading()
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
        )


@me.stateclass
class AppState:
    query_text: str = ""
    # Non-optional ResearchSession so Mesop registers the model in pydantic_model_cache
    # (Union types like ResearchSession | None are skipped and break deserialization).
    session: ResearchSession = field(default_factory=ResearchSession)
    loading: bool = False


def _render_results(session: ResearchSession) -> None:
    CardTimeline(session)
    PanelClaims(session)
    PanelSources(session)
    PanelReport(session)


def _on_query_input(e: me.InputEvent) -> None:
    state: AppState = me.state(AppState)
    state.query_text = e.value


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
    logger.info("UI submit query=%r session_id=%s", query_text, state.session.id)
    yield

    try:
        from a2a_research.workflow import run_workflow_async

        result = await run_workflow_async(query_text)
        state.session = result
        logger.info(
            "UI submit completed session_id=%s final_report_chars=%s",
            result.id,
            len(result.final_report),
        )
    except Exception as exc:
        state.session.error = str(exc)
        logger.exception("UI submit failed query=%r", query_text)
    finally:
        state.loading = False

    yield
