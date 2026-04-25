"""HTTP test helpers for in-memory A2A ASGI applications."""

from __future__ import annotations

import warnings
from typing import Any

import httpx
from a2a.client import Client as SDKClient
from a2a.client import ClientConfig, create_client
from a2a.types import Message, SendMessageRequest, StreamResponse, Task

from core import build_message


class MultiAppTransport(httpx.AsyncBaseTransport):
    def __init__(self, apps_by_url: dict[str, Any]) -> None:
        self._transports = {
            base_url.rstrip("/"): httpx.ASGITransport(app=app)
            for base_url, app in apps_by_url.items()
        }

    async def handle_async_request(
        self, request: httpx.Request
    ) -> httpx.Response:
        base_url = f"{request.url.scheme}://{request.url.host}"
        if request.url.port is not None:
            base_url = f"{base_url}:{request.url.port}"
        transport = self._transports[base_url]
        return await transport.handle_async_request(request)

    async def aclose(self) -> None:
        for transport in self._transports.values():
            await transport.aclose()


def make_multi_app_client(
    apps_by_url: dict[str, Any],
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=MultiAppTransport(apps_by_url),
        timeout=30.0,
        follow_redirects=True,
    )


async def build_sdk_client(
    http_client: httpx.AsyncClient, url: str
) -> SDKClient:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return await create_client(
            url,
            client_config=ClientConfig(
                httpx_client=http_client, streaming=True
            ),
        )


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
        result.status.CopyFrom(item.status_update.status)
    return result


async def send_and_get_result(
    client: SDKClient,
    *,
    payload: dict[str, Any] | None = None,
    text: str = "",
) -> Task | Message:
    result: Task | Message | None = None
    async for response in client.send_message(
        SendMessageRequest(message=build_message(data=payload, text=text))
    ):
        result = _accumulate_stream(result, response)
    if result is None:
        raise AssertionError("A2A client returned no task or message")
    return result
