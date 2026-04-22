"""Main driver for the v1 5-agent coordinator workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.logging.app_logging import get_logger
from a2a_research.workflow.coordinator_fact_checker import (
    run_fact_checker_step,
)
from a2a_research.workflow.coordinator_planner import run_planner_step
from a2a_research.workflow.coordinator_reader import run_reader_step
from a2a_research.workflow.coordinator_searcher import run_searcher_step
from a2a_research.workflow.coordinator_synthesizer import (
    run_synthesizer_step,
)

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import ResearchSession

logger = get_logger(__name__)

__all__ = ["drive"]


async def drive(
    session: ResearchSession, client: A2AClient, query: str
) -> None:
    claims, seed_queries, abort = await run_planner_step(
        session, client, query
    )
    if abort:
        return

    hits, _search_errors, abort = await run_searcher_step(
        session, client, query, seed_queries
    )
    if abort:
        return

    sources, successful_pages, abort = await run_reader_step(
        session, client, query, claims, hits
    )
    if abort:
        return

    verified, abort = await run_fact_checker_step(
        session, client, query, claims, successful_pages, sources
    )
    if abort:
        return

    await run_synthesizer_step(session, client, query, verified, sources)
