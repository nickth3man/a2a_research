"""HTTP A2A client helper functions."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from a2a.server.context import ServerCallContext
from a2a.types import Message, SendMessageRequest, StreamResponse, Task

from a2a_research.backend.core.a2a.proto import (
    ROLE_USER,
    get_data_part,
    get_text_part,
    make_message,
)
from a2a_research.backend.core.logging.app_logging import get_logger, log_event

logger = get_logger(__name__)


def build_message(
    text: str = "",
    data: dict[str, Any] | None = None,
    *,
    role: Any = ROLE_USER,
    task_id: str | None = None,
    context_id: str | None = None,
) -> Message:
    return make_message(
        text=text,
        data=data,
        role=role,
        task_id=task_id,
        context_id=context_id,
    )


def extract_data_payloads(
    task_or_message: Task | Message,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    parts: list[Any] = []
    if isinstance(task_or_message, Task):
        for artifact in task_or_message.artifacts or []:
            parts.extend(artifact.parts)
    else:
        parts.extend(task_or_message.parts)
    for part in parts:
        payload = get_data_part(part)
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def extract_text(task_or_message: Task | Message) -> str:
    chunks: list[str] = []
    parts: list[Any] = []
    if isinstance(task_or_message, Task):
        for artifact in task_or_message.artifacts or []:
            parts.extend(artifact.parts)
    else:
        parts.extend(task_or_message.parts)
    for part in parts:
        text = get_text_part(part)
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def extract_data_payload_or_warn(
    task_or_message: Task | Message,
) -> dict[str, Any]:
    payloads = extract_data_payloads(task_or_message)
    if not payloads:
        return {}
    if len(payloads) == 1:
        return payloads[0]
    merged: dict[str, Any] = {}
    for payload in payloads:
        merged.update(payload)
    logger.warning(
        "Multiple data payloads found (%s); merging with later keys winning.",
        len(payloads),
    )
    return merged


def _payload_preview(
    payload: dict[str, Any] | None,
) -> tuple[list[str], int, str]:
    if not payload:
        return [], 0, ""
    rendered = json.dumps(payload, default=str, indent=2, sort_keys=True)
    return sorted(payload.keys()), len(rendered.encode("utf-8")), rendered


async def handle_in_process_send(
    handler: Any,
    request: SendMessageRequest,
    role: Any,
    py_logger: Any,
) -> Task | Message:
    """Dispatch to an in-process registry handler and log the response."""
    result_local = await handler.on_message_send(request, ServerCallContext())
    task_state: str | None = None
    task_id_out: str | None = None
    if isinstance(result_local, Task):
        st = getattr(getattr(result_local, "status", None), "state", None)
        task_state = str(st) if st is not None else None
        task_id_out = (
            str(result_local.id) if getattr(result_local, "id", None) else None
        )
    log_event(
        py_logger,
        logging.INFO,
        "a2a.response",
        role=role.value,
        url="in_process",
        result_type=type(result_local).__name__,
        task_state=task_state,
        task_id=task_id_out,
    )
    return cast("Task | Message", result_local)


def _accumulate_stream(
    result: Task | Message | None, item: StreamResponse
) -> Task | Message | None:
    if item.HasField("task"):
        return item.task
    if item.HasField("message"):
        return item.message
    if result is None or not isinstance(result, Task):
        return result
    if item.HasField("artifact_update"):
        result.artifacts.append(item.artifact_update.artifact)
    if item.HasField("status_update"):
        status = item.status_update.status
        result.status.CopyFrom(status)
    return result
