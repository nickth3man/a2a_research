"""LangGraph node factories that dispatch Searcher and Reader peer agents."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from a2a_research.agents.langgraph.fact_checker.node_support import (
    task_error_metadata,
    task_failed,
)
from a2a_research.agents.langgraph.fact_checker.state import FactCheckState  # noqa: TC001
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole, WebSource
from a2a_research.progress import ProgressPhase, emit
from a2a_research.tools import PageContent, WebHit

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient

logger = get_logger(__name__)

__all__ = ["build_ask_reader_node", "build_ask_searcher_node"]


def build_ask_searcher_node(client: A2AClient) -> Any:
    async def ask_searcher(state: FactCheckState) -> dict[str, Any]:
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
        from a2a_research.a2a import extract_data_payloads

        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.FACT_CHECKER,
            3,
            5,
            f"round_{round_number}_search",
            detail=f"queries={len(queries)}",
        )
        task = await client.send(
            AgentRole.SEARCHER,
            payload={"queries": queries, "session_id": session_id},
        )
        payloads = extract_data_payloads(task)
        data = payloads[0] if payloads else {}
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
        return {
            "hits": hits,
            "pending_urls": pending_urls,
            "pending_queries": [],
            "errors": errors,
            "search_exhausted": exhausted,
        }

    return ask_searcher


def build_ask_reader_node(client: A2AClient) -> Any:
    async def ask_reader(state: FactCheckState) -> dict[str, Any]:
        urls = list(state.get("pending_urls") or [])
        session_id = str(state.get("session_id") or "")
        round_number = int(state.get("round") or 0) + 1
        if not urls:
            return {"evidence": [], "sources": [], "errors": [], "pending_urls": []}
        from a2a_research.a2a import extract_data_payloads

        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.FACT_CHECKER,
            3,
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
        payloads = extract_data_payloads(task)
        data = payloads[0] if payloads else {}
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
        return {
            "evidence": successful_pages,
            "sources": sources,
            "errors": errors,
            "pending_urls": [],
        }

    return ask_reader
