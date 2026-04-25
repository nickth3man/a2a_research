"""HTTP A2A client wrapper over the official SDK client."""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Any

import httpx
from a2a.client import Client as SDKClient
from a2a.client import ClientConfig, create_client
from a2a.types import Message, SendMessageRequest, Task

from core.a2a.client_helpers import (
    _accumulate_stream,
    _payload_preview,
    build_message,
    extract_data_payload_or_warn,
    extract_data_payloads,
    extract_text,
    handle_in_process_send,
)
from core.a2a.registry import AgentRegistry, get_registry
from core.logging.app_logging import get_logger, log_event
from core.progress import emit_handoff
from core.settings import settings

if TYPE_CHECKING:
    from core import AgentRole

logger = get_logger(__name__)

__all__ = [
    "A2AClient",
    "build_message",
    "extract_data_payload_or_warn",
    "extract_data_payloads",
    "extract_text",
]


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

    @property
    def registry(self) -> AgentRegistry:
        """Access the agent registry."""
        return self._registry

    async def _get_httpx_client(self) -> httpx.AsyncClient:
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient(
                timeout=settings.workflow_timeout
            )
        return self._httpx_client

    async def _get_sdk_client(self, role: AgentRole) -> SDKClient:
        key = role.value
        if key in self._sdk_clients:
            return self._sdk_clients[key]
        http_client = await self._get_httpx_client()
        url = self._registry.get_url(role)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            sdk_client = await create_client(
                url,
                client_config=ClientConfig(
                    httpx_client=http_client, streaming=True
                ),
            )
        self._sdk_clients[key] = sdk_client
        return sdk_client

    def build_registry_snapshot(self) -> dict[str, Any]:
        return self._registry.build_snapshot()

    async def send(
        self,
        role: AgentRole,
        payload: dict[str, Any] | None = None,
        *,
        text: str = "",
        task_id: str | None = None,
        context_id: str | None = None,
        from_role: AgentRole | None = None,
    ) -> Task | Message:
        send_payload = dict(payload) if payload is not None else None
        if from_role is not None and send_payload is not None:
            send_payload["handoff_from"] = str(from_role.value)
        message = build_message(
            text=text,
            data=send_payload,
            task_id=task_id,
            context_id=context_id,
        )
        session_id = send_payload.get("session_id") if send_payload else None
        if session_id and from_role is not None:
            payload_keys, payload_bytes, payload_preview = _payload_preview(
                send_payload
            )
            emit_handoff(
                direction="sent",
                role=from_role,
                peer_role=role,
                payload_keys=payload_keys,
                payload_bytes=payload_bytes,
                payload_preview=payload_preview,
                session_id=str(session_id),
            )
        request = SendMessageRequest(message=message)
        url = self._registry.get_url(role)
        logger.info(
            "A2A.send role=%s url=%s task_id=%s payload_keys=%s",
            role.value,
            url,
            task_id,
            sorted(send_payload or {}),
        )
        if self._registry.has_handler(role):
            handler = self._registry.get_handler(role)
            return await handle_in_process_send(handler, request, role, logger)
        try:
            client = await self._get_sdk_client(role)
            result: Task | Message | None = None
            async for item in client.send_message(request):
                result = _accumulate_stream(result, item)
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
            msg = (
                f"Agent not reachable for role '{role.value}' at {url}: {exc}"
            )
            raise RuntimeError(msg) from exc
        if result is None:
            msg = f"Agent '{role.value}' returned no task or message."
            raise RuntimeError(msg)
        response_task_state: str | None = None
        response_task_id: str | None = None
        if isinstance(result, Task):
            st = getattr(getattr(result, "status", None), "state", None)
            response_task_state = str(st) if st is not None else None
            response_task_id = (
                str(result.id) if getattr(result, "id", None) else None
            )
        log_event(
            logger,
            logging.INFO,
            "a2a.response",
            role=role.value,
            url=url,
            result_type=type(result).__name__,
            task_state=response_task_state,
            task_id=response_task_id,
        )
        return result

    async def aclose(self) -> None:
        for client in self._sdk_clients.values():
            await client.close()
        if self._httpx_client is not None:
            await self._httpx_client.aclose()
