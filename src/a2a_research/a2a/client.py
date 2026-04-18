"""HTTP A2A client wrapper over the official SDK client."""

from __future__ import annotations

import logging
import uuid
import warnings
from typing import TYPE_CHECKING, Any

import httpx
from a2a.client import A2AClient as SDKClient
from a2a.types import (
    AgentCard,
    DataPart,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    Task,
    TextPart,
)

from a2a_research.a2a.registry import AgentRegistry, get_registry
from a2a_research.app_logging import get_logger, log_event
from a2a_research.progress import emit_handoff
from a2a_research.settings import settings

if TYPE_CHECKING:
    from a2a_research.models import AgentRole

logger = get_logger(__name__)

__all__ = [
    "A2AClient",
    "build_message",
    "extract_data_payload_or_warn",
    "extract_data_payloads",
    "extract_text",
]


def build_message(
    text: str = "",
    data: dict[str, Any] | None = None,
    *,
    role: Role = Role.user,
    task_id: str | None = None,
    context_id: str | None = None,
) -> Message:
    parts: list[Part] = []
    if text:
        parts.append(Part(root=TextPart(text=text)))
    if data is not None:
        parts.append(Part(root=DataPart(data=data)))
    if not parts:
        parts.append(Part(root=TextPart(text="")))
    return Message(
        message_id=str(uuid.uuid4()),
        role=role,
        parts=parts,
        task_id=task_id,
        context_id=context_id,
    )


def extract_data_payloads(task_or_message: Task | Message) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    if isinstance(task_or_message, Task):
        for artifact in task_or_message.artifacts or []:
            for part in artifact.parts:
                root = getattr(part, "root", part)
                if isinstance(root, DataPart):
                    payloads.append(dict(root.data))
    else:
        for part in task_or_message.parts:
            root = getattr(part, "root", part)
            if isinstance(root, DataPart):
                payloads.append(dict(root.data))
    return payloads


def extract_text(task_or_message: Task | Message) -> str:
    chunks: list[str] = []
    if isinstance(task_or_message, Task):
        for artifact in task_or_message.artifacts or []:
            for part in artifact.parts:
                root = getattr(part, "root", part)
                if isinstance(root, TextPart):
                    chunks.append(root.text)
    else:
        for part in task_or_message.parts:
            root = getattr(part, "root", part)
            if isinstance(root, TextPart):
                chunks.append(root.text)
    return "\n".join(chunk for chunk in chunks if chunk)


def extract_data_payload_or_warn(task_or_message: Task | Message) -> dict[str, Any]:
    payloads = extract_data_payloads(task_or_message)
    if not payloads:
        return {}
    if len(payloads) == 1:
        return payloads[0]
    merged: dict[str, Any] = {}
    for payload in payloads:
        merged.update(payload)
    logger.warning(
        "Multiple data payloads found (%s); merging with later keys winning.", len(payloads)
    )
    return merged


class A2AClient:
    """Thin async client that dispatches to HTTP-backed A2A services."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._registry = registry or get_registry()
        self._httpx_client = httpx_client
        self._sdk_clients: dict[str, SDKClient] = {}
        self._cards: dict[str, AgentCard] = {}

    async def _get_httpx_client(self) -> httpx.AsyncClient:
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient(timeout=settings.workflow_timeout)
        return self._httpx_client

    async def _get_sdk_client(self, role: AgentRole) -> SDKClient:
        key = role.value
        if key in self._sdk_clients:
            return self._sdk_clients[key]
        http_client = await self._get_httpx_client()
        url = self._registry.get_url(role)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            sdk_client = SDKClient(httpx_client=http_client, url=url)
        self._cards[key] = await sdk_client.get_card()
        self._sdk_clients[key] = sdk_client
        return sdk_client

    async def send(
        self,
        role: AgentRole,
        payload: dict[str, Any] | None = None,
        *,
        text: str = "",
        task_id: str | None = None,
        context_id: str | None = None,
    ) -> Task | Message:
        message = build_message(text=text, data=payload, task_id=task_id, context_id=context_id)
        request = SendMessageRequest(
            id=str(uuid.uuid4()),
            params=MessageSendParams(message=message),
        )
        url = self._registry.get_url(role)
        logger.info(
            "A2A.send role=%s url=%s task_id=%s payload_keys=%s",
            role.value,
            url,
            task_id,
            sorted(payload or {}),
        )
        if self._registry.has_handler(role):
            handler = self._registry.get_handler(role)
            params = MessageSendParams(message=message)
            result_local = await handler.on_message_send(params)
            task_state: str | None = None
            task_id_out: str | None = None
            if isinstance(result_local, Task):
                st = getattr(getattr(result_local, "status", None), "state", None)
                task_state = str(st) if st is not None else None
                task_id_out = str(result_local.id) if getattr(result_local, "id", None) else None
            log_event(
                logger,
                logging.INFO,
                "a2a.response",
                role=role.value,
                url="in_process",
                result_type=type(result_local).__name__,
                task_state=task_state,
                task_id=task_id_out,
            )
            return result_local
        try:
            client = await self._get_sdk_client(role)
            response = await client.send_message(request)
        except httpx.ConnectError as exc:
            log_event(
                logger,
                logging.INFO,
                "a2a.send_failed",
                role=role.value,
                url=url,
                error_type="ConnectError",
                error=str(exc),
            )
            msg = f"Agent not reachable for role '{role.value}' at {url}: {exc}"
            raise RuntimeError(msg) from exc
        if isinstance(response.root, JSONRPCErrorResponse):
            log_event(
                logger,
                logging.INFO,
                "a2a.jsonrpc_error",
                role=role.value,
                url=url,
                message=response.root.error.message,
            )
            msg = f"Agent '{role.value}' returned an A2A error: {response.root.error.message}"
            raise RuntimeError(msg)
        result = response.root.result
        task_state: str | None = None
        task_id_out: str | None = None
        if isinstance(result, Task):
            st = getattr(getattr(result, "status", None), "state", None)
            task_state = str(st) if st is not None else None
            task_id_out = str(result.id) if getattr(result, "id", None) else None
        log_event(
            logger,
            logging.INFO,
            "a2a.response",
            role=role.value,
            url=url,
            result_type=type(result).__name__,
            task_state=task_state,
            task_id=task_id_out,
        )
        return result

    async def aclose(self) -> None:
        if self._httpx_client is not None:
            await self._httpx_client.aclose()
