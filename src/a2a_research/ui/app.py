import asyncio

import mesop as me

from a2a_research.models import AgentStatus, ResearchSession
from a2a_research.ui.components import (
    agent_timeline_card,
    claims_panel,
    error_banner,
    loading_card,
    query_input_card,
    report_panel,
    sources_panel,
)


@me.page(path="/", title="A2A Research — Multi-Agent Research System")
def main_page():
    state: AppState = me.state(AppState)

    with me.box(
        style=me.Style(
            max_width=900,
            margin=me.Margin(left="auto", right="auto"),
            padding=me.Padding(left=16, right=16, top=24, bottom=24),
            font_family="system-ui, -apple-system, sans-serif",
        )
    ):
        _render_header()
        _render_instructions()

        if state.error:
            error_banner(state.error)

        if state.loading:
            if state.session:
                loading_card(state.session)
        else:
            if state.session and _has_results(state.session):
                _render_results(state.session)
            else:
                _render_empty_state()

        query_input_card(
            on_submit=_on_submit,
            on_query_input=_on_query_input,
            query_text=state.query_text,
        )


@me.stateclass
class AppState:
    query_text: str = ""
    session: ResearchSession | None = None
    loading: bool = False
    error: str | None = None


def _render_header():
    with me.box(
        style=me.Style(
            border=me.Border(
                bottom=me.BorderSide(width=2, color="#e5e7eb"),
            ),
            padding=me.Padding(bottom=16),
            margin=me.Margin(bottom=24),
        )
    ):
        me.text("A2A Research System", type="headline-4")
        me.text(
            "Local-first 4-agent pipeline: Researcher → Analyst → Verifier → Presenter",
            style=me.Style(font_size="14px", color="#6b7280", margin=me.Margin(top=4)),
        )


def _render_instructions():
    with me.box(
        style=me.Style(
            background="#eff6ff",
            border=me.Border(
                top=me.BorderSide(width=1, color="#bfdbfe"),
                right=me.BorderSide(width=1, color="#bfdbfe"),
                bottom=me.BorderSide(width=1, color="#bfdbfe"),
                left=me.BorderSide(width=1, color="#bfdbfe"),
            ),
            border_radius=8,
            padding=me.Padding(top=14, right=14, bottom=14, left=14),
            margin=me.Margin(bottom=24),
        )
    ):
        me.markdown(
            "**How it works:** Enter a research query to start a session. "
            "The pipeline retrieves documents from the RAG corpus, decomposes claims, "
            "verifies evidence, and renders a final markdown report — "
            "all via in-process A2A-shaped agent contracts.",
        )


def _render_empty_state():
    with me.box(
        style=me.Style(
            text_align="center",
            background="#f9fafb",
            border=me.Border(
                top=me.BorderSide(width=1, color="#d1d5db"),
                right=me.BorderSide(width=1, color="#d1d5db"),
                bottom=me.BorderSide(width=1, color="#d1d5db"),
                left=me.BorderSide(width=1, color="#d1d5db"),
            ),
            border_radius=10,
            padding=me.Padding(top=48, right=24, bottom=48, left=24),
            margin=me.Margin(bottom=20),
        )
    ):
        me.text(
            "No active session — enter a query above to begin.",
            style=me.Style(color="#6b7280", font_size="15px"),
        )


def _render_results(session: ResearchSession):
    agent_timeline_card(session)
    claims_panel(session)
    sources_panel(session)
    report_panel(session)


def _has_results(session: ResearchSession) -> bool:
    if not session.agent_results:
        return False
    return all(
        r.status in (AgentStatus.COMPLETED, AgentStatus.FAILED)
        for r in session.agent_results.values()
    ) or bool(session.final_report)


def _on_query_input(e: me.InputEvent):
    state: AppState = me.state(AppState)
    state.query_text = e.value


async def _on_submit(e: me.ClickEvent):
    state: AppState = me.state(AppState)
    query_text = state.query_text.strip()

    if not query_text:
        state.error = "Enter a research query before running the pipeline."
        return

    state.loading = True
    state.error = None
    state.session = ResearchSession(query=query_text)

    try:
        from a2a_research.graph import run_research_sync

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, run_research_sync, query_text)
        state.session = result
    except Exception as exc:
        state.error = str(exc)
    finally:
        state.loading = False
