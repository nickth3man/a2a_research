"""HTTP test helpers for in-memory A2A ASGI applications."""

from __future__ import annotations

import warnings
from typing import Any

import httpx
from a2a.client import A2AClient as SDKClient
from a2a.types import JSONRPCErrorResponse, Message, MessageSendParams, SendMessageRequest, Task

from a2a_research.a2a.client import build_message


class MultiAppTransport(httpx.AsyncBaseTransport):
    def __init__(self, apps_by_url: dict[str, Any]) -> None:
        self._transports = {
            base_url.rstrip("/"): httpx.ASGITransport(app=app)
            for base_url, app in apps_by_url.items()
        }

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        base_url = f"{request.url.scheme}://{request.url.host}"
        if request.url.port is not None:
            base_url = f"{base_url}:{request.url.port}"
        transport = self._transports[base_url]
        return await transport.handle_async_request(request)

    async def aclose(self) -> None:
        for transport in self._transports.values():
            await transport.aclose()


def make_multi_app_client(apps_by_url: dict[str, Any]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=MultiAppTransport(apps_by_url), timeout=30.0)


def build_sdk_client(http_client: httpx.AsyncClient, url: str) -> SDKClient:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return SDKClient(httpx_client=http_client, url=url)


async def send_and_get_result(
    client: SDKClient, *, payload: dict[str, Any] | None = None, text: str = ""
) -> Task | Message:
    response = await client.send_message(
        SendMessageRequest(
            id="1",
            params=MessageSendParams(message=build_message(data=payload, text=text)),
        )
    )
    if isinstance(response.root, JSONRPCErrorResponse):
        raise AssertionError(response.root.error.message)
    return response.root.result
