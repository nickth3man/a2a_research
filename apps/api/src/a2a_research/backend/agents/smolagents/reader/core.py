"""Reader core logic."""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import Any, cast

from a2a_research.backend.agents.smolagents.reader.agent import build_agent
from a2a_research.backend.core.logging.app_logging import get_logger, log_event
from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.progress import (
    emit_llm_response,
    emit_prompt,
    using_session,
)
from a2a_research.backend.core.settings import settings as _app_settings
from a2a_research.backend.core.utils.json_utils import parse_json_safely
from a2a_research.backend.tools import PageContent, fetch_many

logger = get_logger(__name__)


async def read_urls(
    urls: list[str], *, max_chars: int = 8000, session_id: str = ""
) -> list[PageContent]:
    if not urls:
        return []

    log_event(
        logger,
        logging.INFO,
        "reader.read_urls_start",
        urls=urls,
        max_chars=max_chars,
    )
    prompt = (
        "URLs to read:\n"
        + "\n".join(f"- {url}" for url in urls)
        + f"\n\nmax_chars={max_chars}. Return JSON only with a pages array."
    )

    emit_prompt(
        AgentRole.READER,
        "react_loop",
        prompt,
        model=_app_settings.llm.model,
        session_id=session_id,
    )
    agent = build_agent()
    runner = cast("Any", agent.run)
    started = perf_counter()
    with using_session(session_id):
        raw_output = await asyncio.to_thread(runner, prompt)
    emit_llm_response(
        AgentRole.READER,
        "react_loop",
        str(raw_output),
        elapsed_ms=(perf_counter() - started) * 1000,
        model=_app_settings.llm.model,
        session_id=session_id,
    )
    data = parse_json_safely(str(raw_output))
    raw_pages_any = data.get("pages")
    raw_pages: list[object] = (
        raw_pages_any if isinstance(raw_pages_any, list) else []
    )
    pages = [
        PageContent.model_validate(item)
        for item in raw_pages
        if isinstance(item, dict)
    ]
    if pages:
        log_event(
            logger,
            logging.INFO,
            "reader.read_urls_agent_json",
            url_count=len(urls),
            page_count=len(pages),
            via="smolagents_json",
        )
        return pages
    log_event(
        logger,
        logging.INFO,
        "reader.read_urls_fallback",
        url_count=len(urls),
        via="fetch_many_trafilatura",
    )
    return await fetch_many(urls, max_chars=max_chars)
