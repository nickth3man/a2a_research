"""A2A AgentExecutor for the Reader role."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import TaskState

from a2a_research.a2a.compat import build_http_app as build_starlette_http_app
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.smolagents.reader.card import READER_CARD
from a2a_research.agents.smolagents.reader.core import read_urls
from a2a_research.agents.smolagents.reader.events import (
    emit_page_progress,
    enqueue_reader_result,
    log_reader_completion,
)
from a2a_research.agents.smolagents.reader.payload import (
    _coerce_str_list,
    _extract_payload,
)
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit

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

        emit_page_progress(session_id, pages, urls)
        await enqueue_reader_result(
            task, event_queue, pages, urls, status, error_text, session_id
        )
        logger.info(
            "Reader task_id=%s urls=%s pages=%s",
            task.id,
            len(urls),
            len(pages),
        )
        log_reader_completion(logger, task, urls, pages)

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=ReaderExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=READER_CARD,
    )
    return build_starlette_http_app(
        agent_card=READER_CARD, http_handler=handler
    )
