"""HTTP contract test for the FactChecker service."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from a2a.types import Task

from agents.langgraph.fact_checker import card as fc_card
from agents.langgraph.fact_checker import (
    main as fact_checker_main,
)
from agents.langgraph.fact_checker import (
    verify_route as fc_verify,
)
from core import AgentRegistry, extract_data_payloads
from tests.http_harness import (
    build_sdk_client,
    make_multi_app_client,
    send_and_get_result,
)


@pytest.mark.asyncio
async def test_fact_checker_http_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fc_card.FACT_CHECKER_CARD.supported_interfaces[
        0
    ].url = "http://localhost:10004"
    model = MagicMock()
    model.ainvoke = AsyncMock(
        return_value=MagicMock(
            content=json.dumps(
                {
                    "verified_claims": [
                        {
                            "id": "c0",
                            "text": "JWST launched in December 2021.",
                            "verdict": "SUPPORTED",
                            "confidence": 0.95,
                            "sources": ["https://nasa.example/jwst"],
                        }
                    ],
                    "follow_up_queries": [],
                }
            )
        )
    )
    monkeypatch.setattr(fc_verify, "get_llm", lambda: model)

    apps = {
        "http://localhost:10004": fact_checker_main.build_http_app(),
    }
    shared_client = make_multi_app_client(apps)

    from core import client as client_module

    def _client_factory(*args: object, **kwargs: object) -> Any:
        return shared_client

    monkeypatch.setattr(client_module.httpx, "AsyncClient", _client_factory)
    monkeypatch.setattr(
        client_module,
        "get_registry",
        lambda: AgentRegistry(
            fact_checker_url="http://localhost:10004",
        ),
    )

    sdk_client = await build_sdk_client(
        shared_client, "http://localhost:10004"
    )
    result = await send_and_get_result(
        sdk_client,
        payload={
            "query": "When did JWST launch?",
            "claims": [
                {"id": "c0", "text": "JWST launched in December 2021."}
            ],
            "evidence": [
                {
                    "url": "https://nasa.example/jwst",
                    "title": "NASA JWST",
                    "markdown": "# NASA\n\nJWST launched December 25, 2021.",
                    "word_count": 6,
                }
            ],
            "sources": [
                {
                    "url": "https://nasa.example/jwst",
                    "title": "NASA JWST",
                    "excerpt": "JWST launched",
                }
            ],
        },
    )
    assert isinstance(result, Task)
    assert extract_data_payloads(result)[0]["verified_claims"][0]["id"] == "c0"
    await shared_client.aclose()
