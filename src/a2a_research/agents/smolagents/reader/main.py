"""A2A AgentExecutor for the Reader role.

Consumes ``{urls: list[str]}`` and returns a Task with a data artifact of
``{pages: [PageContent, …]}``. Pages that fail to fetch are included with
``error != None`` so the FactChecker can distinguish "no evidence" from
"evidence retrieved but empty".
"""

from __future__ import annotations

import asyncio
import json
import logging
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    Artifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from a2a_research.a2a.compat import build_http_app as build_starlette_http_app
from a2a_research.a2a.proto import (
    get_data_part,
    get_text_part,
    make_data_part,
    new_agent_text_message,
)
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.smolagents.reader.agent import build_agent
from a2a_research.agents.smolagents.reader.card import READER_CARD
from a2a_research.app_logging import get_logger, log_event
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import AgentRole
from a2a_research.progress import (
    ProgressPhase,
    emit,
    emit_llm_response,
    emit_prompt,
    using_session,
)
from a2a_research.settings import settings as _app_settings
from a2a_research.tools import PageContent, fetch_many

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["ReaderExecutor", "build_http_app", "read_urls"]


class ReaderExecutor(AgentExecutor):
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        session_id = str(payload.get("session_id") or "")
        handoff_from = payload.get("handoff_from")
        if session_id and handoff_from:
            from a2a_research.progress import emit_handoff

            emit_handoff(
                direction="received",
                role=AgentRole.READER,
                peer_role=str(handoff_from),
                payload_keys=sorted(payload.keys()),
                payload_bytes=len(
                    json.dumps(payload, default=str).encode("utf-8")
                ),
                payload_preview=json.dumps(
                    payload, default=str, indent=2, sort_keys=True
                ),
                session_id=session_id,
            )
        urls = _coerce_str_list(payload.get("urls") or payload.get("url"))
        max_chars_raw = payload.get("max_chars")
        max_chars = (
            int(max_chars_raw)
            if isinstance(max_chars_raw, (int, str))
            else 8000
        )
        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.READER,
            2,
            5,
            "reader_started",
        )

        try:
            pages = await read_urls(
                urls, max_chars=max_chars, session_id=session_id
            )
            status = TaskState.TASK_STATE_COMPLETED
            error_text: str | None = None
        except Exception as exc:
            logger.exception("Reader failed task_id=%s", task.id)
            pages = []
            status = TaskState.TASK_STATE_FAILED
            error_text = str(exc)

        for index, page in enumerate(pages, start=1):
            emit(
                session_id,
                ProgressPhase.STEP_SUBSTEP,
                AgentRole.READER,
                2,
                5,
                f"fetch_url_{index}",
                substep_index=index,
                substep_total=max(len(urls), 1),
                detail=page.error or page.title or page.url,
            )

        artifact = Artifact(
            artifact_id="extracted-pages",
            name="extracted-pages",
            parts=[
                make_data_part(
                    {"pages": [p.model_dump(mode="json") for p in pages]}
                )
            ],
        )
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task.id,
                context_id=task.context_id,
                artifact=artifact,
                append=False,
                last_chunk=True,
            )
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task.id,
                context_id=task.context_id,
                status=TaskStatus(
                    state=status,
                    message=new_agent_text_message(error_text)
                    if error_text
                    else None,
                ),
            )
        )
        emit(
            session_id,
            ProgressPhase.STEP_COMPLETED
            if status == TaskState.TASK_STATE_COMPLETED
            else ProgressPhase.STEP_FAILED,
            AgentRole.READER,
            2,
            5,
            "reader_completed"
            if status == TaskState.TASK_STATE_COMPLETED
            else "reader_failed",
            detail=f"urls={len(urls)} pages={len(pages)}",
        )
        logger.info(
            "Reader task_id=%s urls=%s pages=%s",
            task.id,
            len(urls),
            len(pages),
        )
        log_event(
            logger,
            logging.INFO,
            "reader.task_completed",
            task_id=str(task.id),
            urls=urls,
            page_count=len(pages),
            pages_summary=[
                {
                    "url": p.url,
                    "ok": not bool(p.error),
                    "error": p.error,
                    "words": p.word_count,
                }
                for p in pages
            ],
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


def _extract_payload(context: RequestContext) -> dict[str, object]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            return data_part
        text_part = get_text_part(part)
        if text_part:
            try:
                data = json.loads(text_part)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                return dict(data)
    return {}


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


def _coerce_str_list(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=ReaderExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=READER_CARD,
    )
    return build_starlette_http_app(
        agent_card=READER_CARD, http_handler=handler
    )
