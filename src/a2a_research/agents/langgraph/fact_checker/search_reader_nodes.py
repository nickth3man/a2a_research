"""LangGraph nodes that call Searcher and Reader over A2A.

The Fact Checker graph owns verification state; these nodes are thin adapters to
the Searcher (:10002) and Reader (:10003) services. Progress substeps use those
roles so the UI reflects search/read work, not only the Fact Checker role.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from a2a_research.agents.langgraph.fact_checker.node_support import (
    task_error_metadata,
    task_failed,
)
from a2a_research.agents.langgraph.fact_checker.state import FactCheckState  # noqa: TC001
from a2a_research.app_logging import get_logger, log_event
from a2a_research.models import AgentRole, WebSource
from a2a_research.progress import ProgressPhase, emit
from a2a_research.tools import PageContent, WebHit

logger = get_logger(__name__)

__all__ = ["build_ask_reader_node", "build_ask_searcher_node"]


def build_ask_searcher_node() -> Any:
    async def ask_searcher(state: FactCheckState) -> dict[str, Any]:
        client = cast("Any", state.get("_client"))
        queries = list(state.get("pending_queries") or [])
        session_id = str(state.get("session_id") or "")
        round_number = int(state.get("round") or 0) + 1
        if not queries:
            return {
                "hits": [],
                "pending_urls": [],
                "pending_queries": [],
                "errors": [],
                "search_exhausted": True,
            }
        from a2a_research.a2a import extract_data_payload_or_warn

        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.SEARCHER,
            1,
            5,
            f"round_{round_number}_search",
            detail=f"queries={len(queries)}",
        )
        task = await client.send(
            AgentRole.SEARCHER,
            payload={"queries": queries, "session_id": session_id},
        )
        data = extract_data_payload_or_warn(task)
        raw_hits = data.get("hits") or []
        raw_errors = data.get("errors") or []
        providers_successful = data.get("providers_successful") or []

        hits = [WebHit.model_validate(h) for h in raw_hits]
        errors: list[str] = [f"Searcher: {e}" for e in raw_errors if isinstance(e, str)]
        task_err = task_error_metadata(task)
        if task_failed(task) and task_err:
            errors.append(f"Searcher task failed: {task_err}")

        exhausted = not providers_successful and not hits
        pending_urls = [h.url for h in hits[:6]]

        logger.info(
            "FactChecker ask_searcher queries=%s hits=%s urls=%s errors=%s exhausted=%s",
            len(queries),
            len(hits),
            len(pending_urls),
            len(errors),
            exhausted,
        )
        log_event(
            logger,
            logging.INFO,
            "fact_checker.searcher_round",
            queries=queries,
            hit_count=len(hits),
            pending_urls=pending_urls,
            hit_urls_sample=[h.url for h in hits[:12]],
            providers_successful=providers_successful,
            errors=errors,
            search_exhausted=exhausted,
        )
        return {
            "hits": hits,
            "pending_urls": pending_urls,
            "pending_queries": [],
            "errors": errors,
            "search_exhausted": exhausted,
        }

    return ask_searcher


def build_ask_reader_node() -> Any:
    async def ask_reader(state: FactCheckState) -> dict[str, Any]:
        client = cast("Any", state.get("_client"))
        urls = list(state.get("pending_urls") or [])
        session_id = str(state.get("session_id") or "")
        round_number = int(state.get("round") or 0) + 1
        if not urls:
            return {"evidence": [], "sources": [], "errors": [], "pending_urls": []}
        from a2a_research.a2a import extract_data_payload_or_warn

        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.READER,
            2,
            5,
            f"round_{round_number}_read",
            detail=f"urls={len(urls)}",
        )
        task = await client.send(
            AgentRole.READER,
            payload={
                "urls": urls,
                "session_id": session_id,
                "claims": [claim.model_dump(mode="json") for claim in (state.get("claims") or [])],
            },
        )
        data = extract_data_payload_or_warn(task)
        raw_pages = data.get("pages") or []
        pages = [PageContent.model_validate(p) for p in raw_pages if p]

        successful_pages = [p for p in pages if not p.error and p.markdown]
        sources = [
            WebSource(
                url=p.url,
                title=p.title or p.url,
                excerpt=(p.markdown[:280] if p.markdown else ""),
            )
            for p in successful_pages
        ]

        errors: list[str] = []
        fetch_failures = [p for p in pages if p.error]
        if urls and pages and not successful_pages and fetch_failures:
            reasons = "; ".join(f"{p.url}: {p.error}" for p in fetch_failures[:3] if p.error)
            errors.append(f"Reader: every requested URL failed to extract ({reasons})")
        task_err = task_error_metadata(task)
        if task_failed(task) and task_err:
            errors.append(f"Reader task failed: {task_err}")

        logger.info(
            "FactChecker ask_reader urls=%s pages_ok=%s failures=%s errors=%s",
            len(urls),
            len(successful_pages),
            len(fetch_failures),
            len(errors),
        )
        log_event(
            logger,
            logging.INFO,
            "fact_checker.reader_round",
            urls=urls,
            pages_ok=len(successful_pages),
            failures=len(fetch_failures),
            page_results=[
                {"url": p.url, "ok": not bool(p.error), "error": p.error, "words": p.word_count}
                for p in pages
            ],
            errors=errors,
        )
        return {
            "evidence": successful_pages,
            "sources": sources,
            "errors": errors,
            "pending_urls": [],
        }

    return ask_reader
