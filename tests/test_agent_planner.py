"""Planner executor + flow tests with LLM mocked."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from a2a_research.a2a import A2AClient, AgentRegistry, extract_data_payloads
from a2a_research.agents.pocketflow.planner import PlannerExecutor, plan
from a2a_research.agents.pocketflow.planner import nodes as planner_nodes
from a2a_research.models import AgentRole


def _fake_llm(content: str) -> Any:
    model = MagicMock()
    model.invoke.return_value = MagicMock(content=content)
    return model


@pytest.mark.asyncio
async def test_plan_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "claims": [
            {"id": "c0", "text": "JWST launched in December 2021."},
            {"id": "c1", "text": "JWST has a 6.5 m primary mirror."},
        ],
        "seed_queries": ["JWST launch date", "JWST primary mirror diameter"],
    }
    monkeypatch.setattr(planner_nodes, "get_llm", lambda: _fake_llm(json.dumps(payload)))

    claims, seeds = await plan("When did JWST launch and what is its mirror size?")
    assert [c.text for c in claims] == [
        "JWST launched in December 2021.",
        "JWST has a 6.5 m primary mirror.",
    ]
    assert seeds == ["JWST launch date", "JWST primary mirror diameter"]


@pytest.mark.asyncio
async def test_plan_falls_back_on_empty_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planner_nodes, "get_llm", lambda: _fake_llm(""))

    claims, seeds = await plan("What is the speed of sound?")
    assert len(claims) == 1
    assert "speed of sound" in claims[0].text
    assert seeds == ["What is the speed of sound?"]


@pytest.mark.asyncio
async def test_executor_returns_plan_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "claims": [{"id": "c0", "text": "Claim A"}],
        "seed_queries": ["query A"],
    }
    monkeypatch.setattr(planner_nodes, "get_llm", lambda: _fake_llm(json.dumps(payload)))

    registry = AgentRegistry()
    registry.register_factory(AgentRole.PLANNER, PlannerExecutor)
    client = A2AClient(registry)

    task = await client.send(AgentRole.PLANNER, payload={"query": "test?"}, text="test?")
    data = extract_data_payloads(task)[0]
    assert data["query"] == "test?"
    assert data["claims"][0]["text"] == "Claim A"
    assert data["seed_queries"] == ["query A"]
