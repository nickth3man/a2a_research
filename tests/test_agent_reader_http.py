"""HTTP contract test for the Reader service."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from a2a.types import Task

from a2a_research.backend.agents.smolagents.reader import core as reader_core
from a2a_research.backend.agents.smolagents.reader import main as reader_main
from a2a_research.backend.core.a2a.client import extract_data_payloads
from a2a_research.backend.core.models import AgentRole
from tests.http_harness import build_sdk_client, send_and_get_result


class _FakeJSONAgent:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def run(self, prompt: str) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_reader_http_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reader_core,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "pages": [
                    {
                        "url": "https://a.example",
                        "title": "A",
                        "markdown": "# A",
                        "word_count": 1,
                    }
                ]
            }
        ),
    )

    from a2a_research.backend.core.settings import settings as test_settings

    monkeypatch.setattr(test_settings, "reader_url", "http://localhost:10003")

    # Rebuild agent cards with patched URL, then patch reader app
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore

    import a2a_research.backend.core.a2a.cards as cards_mod
    from a2a_research.backend.core.a2a.compat import (
        build_http_app as build_starlette_http_app,
    )

    monkeypatch.setattr(cards_mod, "AGENT_CARDS", cards_mod.build_cards())
    _new_card = cards_mod.get_card(AgentRole.READER)

    def _patched_build_http_app() -> Any:
        handler = DefaultRequestHandler(
            agent_executor=reader_main.ReaderExecutor(),
            task_store=InMemoryTaskStore(),
            agent_card=_new_card,
        )
        return build_starlette_http_app(
            agent_card=_new_card, http_handler=handler
        )

    monkeypatch.setattr(reader_main, "build_http_app", _patched_build_http_app)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=reader_main.build_http_app()),
        base_url="http://localhost:10003",
    ) as http_client:
        client = await build_sdk_client(http_client, "http://localhost:10003")
        result = await send_and_get_result(
            client, payload={"urls": ["https://a.example"]}
        )

    assert isinstance(result, Task)
    assert (
        extract_data_payloads(result)[0]["pages"][0]["url"]
        == "https://a.example"
    )
