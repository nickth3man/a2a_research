"""Searcher core logic."""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import Any, cast

from a2a.types import TaskState

from a2a_research.agents.smolagents.searcher.agent import build_agent
from a2a_research.agents.smolagents.searcher.results import (
    merge_with_fallback,
    parse_search_results,
)
from a2a_research.logging.app_logging import get_logger, log_event
from a2a_research.models import AgentRole
from a2a_research.progress import (
    ProgressPhase,
    emit,
    emit_llm_response,
    emit_prompt,
    using_session,
)
from a2a_research.settings import settings as _app_settings
from a2a_research.tools import WebHit

logger = get_logger(__name__)


class SearcherBatchResult:
    hits: list[WebHit]
    errors: list[str]
    providers_successful: list[str]

    def __init__(
        self,
        hits: list[WebHit] | None = None,
        errors: list[str] | None = None,
        providers_successful: list[str] | None = None,
    ) -> None:
        self.hits = hits or []
        self.errors = errors or []
        self.providers_successful = providers_successful or []


async def search_queries(
    queries: list[str], *, session_id: str = ""
) -> SearcherBatchResult:
    """Run the smolagents Searcher tool-calling loop for ``queries``."""
    if not queries:
        return SearcherBatchResult()

    prompt = (
        "Queries to search:\n"
        + "\n".join(f"- {query}" for query in queries)
        + "\n\nReturn JSON only with keys queries_used and hits."
    )

    with using_session(session_id):
        emit_prompt(
            AgentRole.SEARCHER,
            "react_loop",
            prompt,
            model=_app_settings.llm.model,
            session_id=session_id,
        )
        agent = build_agent()
        runner = cast("Any", agent.run)
        started = perf_counter()
        raw_output = await asyncio.to_thread(runner, prompt)
        emit_llm_response(
            AgentRole.SEARCHER,
            "react_loop",
            str(raw_output),
            elapsed_ms=(perf_counter() - started) * 1000,
            model=_app_settings.llm.model,
            session_id=session_id,
        )
        parsed = parse_search_results(str(raw_output))
        by_url = parsed["by_url"]
        errors = parsed["errors"]
        successful_providers = parsed["successful_providers"]
        queries_used = parsed["queries_used"] or queries

        by_url, errors, successful_providers = await merge_with_fallback(
            by_url, errors, successful_providers, queries
        )

    for index, query in enumerate(queries_used, start=1):
        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.SEARCHER,
            1,
            5,
            f"search_query_{index}",
            substep_index=index,
            substep_total=max(len(queries_used), 1),
            detail=(
                f"query={query[:80]} providers="
                f"{','.join(sorted(successful_providers)) or 'none'}"
            ),
        )
    hits = sorted(by_url.values(), key=lambda h: (-h.score, h.source, h.url))
    logger.info(
        "Searcher searched queries=%s merged_hits=%s"
        " errors=%s successful_providers=%s",
        len(queries),
        len(hits),
        len(errors),
        sorted(successful_providers),
    )
    log_event(
        logger,
        logging.INFO,
        "searcher.batch_completed",
        input_queries=queries,
        queries_used=queries_used,
        merged_hits=len(hits),
        errors=errors,
        successful_providers=sorted(successful_providers),
        top_hit_urls=[h.url for h in hits[:20]],
    )
    return SearcherBatchResult(
        hits=hits,
        errors=errors,
        providers_successful=sorted(successful_providers),
    )


def _derive_status(
    queries: list[str],
    hits: list[WebHit],
    errors: list[str],
    successful_providers: list[str],
) -> tuple[TaskState, str | None]:
    if not queries:
        return TaskState.TASK_STATE_COMPLETED, None
    if not successful_providers and errors:
        return TaskState.TASK_STATE_FAILED, (
            "All web-search providers failed: " + " | ".join(errors)
        )
    return TaskState.TASK_STATE_COMPLETED, None
