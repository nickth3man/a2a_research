"""Planner executor + flow tests with LLM mocked."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.pocketflow.planner import (
    PlannerExecutor,
    plan,
)
from agents.pocketflow.planner import (
    nodes as planner_nodes,
)
from agents.pocketflow.planner import (
    nodes_base as planner_nodes_base,
)
from core import AgentRole
from core.a2a import (
    A2AClient,
    AgentRegistry,
    extract_data_payloads,
)


def _router_llm(
    route_payload: dict[str, Any], decompose_payload: dict[str, Any]
) -> Any:
    model = MagicMock()

    async def ainvoke(messages: list[dict[str, str]]) -> Any:
        system_prompt = messages[0]["content"]
        if "classifier" in system_prompt.lower():
            content = json.dumps(route_payload)
        else:
            content = json.dumps(decompose_payload)
        return MagicMock(content=content)

    model.ainvoke = AsyncMock(side_effect=ainvoke)
    return model


@pytest.mark.asyncio
def _patch_get_llm(monkeypatch: pytest.MonkeyPatch, mock_fn: Any) -> None:
    monkeypatch.setattr(planner_nodes, "get_llm", mock_fn)
    monkeypatch.setattr(planner_nodes_base, "get_llm", mock_fn)


@pytest.mark.asyncio
async def test_plan_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_get_llm(
        monkeypatch,
        lambda: _router_llm(
            {"strategy": "factual"},
            {
                "claims": [
                    {"id": "c0", "text": "JWST launched in December 2021."},
                    {"id": "c1", "text": "JWST has a 6.5 m primary mirror."},
                ],
                "seed_queries": [
                    "JWST launch date",
                    "JWST primary mirror diameter",
                ],
            },
        ),
    )

    claims, seeds = await plan(
        "When did JWST launch and what is its mirror size?"
    )
    assert [c.text for c in claims] == [
        "JWST launched in December 2021.",
        "JWST has a 6.5 m primary mirror.",
    ]
    assert seeds == ["JWST launch date", "JWST primary mirror diameter"]


@pytest.mark.asyncio
async def test_plan_temporal_branch_uses_temporal_strategy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_get_llm(
        monkeypatch,
        lambda: _router_llm(
            {"strategy": "temporal"},
            {
                "claims": [
                    {"id": "c0", "text": "JWST launched on December 25, 2021."}
                ],
                "seed_queries": ["JWST launch date NASA"],
            },
        ),
    )

    claims, seeds = await plan("When did JWST launch?")
    assert claims[0].text == "JWST launched on December 25, 2021."
    assert seeds == ["JWST launch date NASA"]


@pytest.mark.asyncio
async def test_plan_falls_back_on_empty_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_get_llm(
        monkeypatch,
        lambda: _router_llm(
            {"strategy": "fallback"}, {"claims": [], "seed_queries": []}
        ),
    )

    claims, seeds = await plan("What is the speed of sound?")
    assert len(claims) == 1
    assert "speed of sound" in claims[0].text
    assert seeds == ["What is the speed of sound?"]


@pytest.mark.asyncio
async def test_executor_returns_plan_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_get_llm(
        monkeypatch,
        lambda: _router_llm(
            {"strategy": "factual"},
            {
                "claims": [{"id": "c0", "text": "Claim A"}],
                "seed_queries": ["query A"],
            },
        ),
    )

    registry = AgentRegistry()
    registry.register_factory(AgentRole.PLANNER, PlannerExecutor)
    client = A2AClient(registry)

    task = await client.send(
        AgentRole.PLANNER, payload={"query": "test?"}, text="test?"
    )
    data = extract_data_payloads(task)[0]
    assert data["query"] == "test?"
    assert data["claims"][0]["text"] == "Claim A"
    assert data["seed_queries"] == ["query A"]
