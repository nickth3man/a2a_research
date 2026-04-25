"""HTTP contract test for the Planner service."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from a2a.types import Task

from agents.pocketflow.planner import card as planner_card
from agents.pocketflow.planner import (
    nodes as planner_nodes,
)
from agents.pocketflow.planner import (
    nodes_base as planner_nodes_base,
)
from agents.pocketflow.planner.main import build_http_app
from core import extract_data_payloads
from tests.http_harness import build_sdk_client, send_and_get_result


@pytest.mark.asyncio
async def test_planner_http_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    planner_card.PLANNER_CARD.supported_interfaces[
        0
    ].url = "http://localhost:10001"
    model = MagicMock()
    model.ainvoke = AsyncMock(
        side_effect=[
            MagicMock(content=json.dumps({"strategy": "factual"})),
            MagicMock(
                content=json.dumps(
                    {
                        "claims": [{"id": "c0", "text": "Claim A"}],
                        "seed_queries": ["query A"],
                    }
                )
            ),
        ]
    )
    monkeypatch.setattr(planner_nodes, "get_llm", lambda: model)
    monkeypatch.setattr(planner_nodes_base, "get_llm", lambda: model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=build_http_app()),
        base_url="http://localhost:10001",
    ) as http_client:
        client = await build_sdk_client(http_client, "http://localhost:10001")
        result = await send_and_get_result(client, payload={"query": "test?"})

    assert isinstance(result, Task)
    assert extract_data_payloads(result)[0]["claims"][0]["text"] == "Claim A"
