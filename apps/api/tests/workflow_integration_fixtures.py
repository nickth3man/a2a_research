"""Fake agents and success-path fixtures for workflow tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.langgraph.fact_checker import (
    verify_route as fc_verify,
)
from agents.pocketflow.planner import (
    nodes as planner_nodes,
)
from agents.pocketflow.planner import (
    nodes_base as planner_nodes_base,
)
from agents.pydantic_ai.synthesizer import (
    agent as synth_agent,
)
from agents.smolagents.reader import (
    agent as reader_agent,
)
from agents.smolagents.reader import (
    core as reader_core,
)
from agents.smolagents.searcher import (
    agent as searcher_agent,
)
from agents.smolagents.searcher import (
    core as searcher_core,
)
from core import ReportOutput


def _llm_stub(payload: dict[str, Any]) -> Any:
    model = MagicMock()
    model.ainvoke = AsyncMock(
        return_value=MagicMock(content=json.dumps(payload))
    )
    return model


class _FakePydAgent:
    def __init__(self, report: ReportOutput) -> None:
        self._report = report

    async def run(self, prompt: str) -> Any:
        return SimpleNamespace(output=self._report)


class _FakeJSONAgent:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def run(self, prompt: str) -> str:
        return json.dumps(self._payload)


def _configure_success_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner_model = MagicMock()
    planner_model.ainvoke = AsyncMock(
        side_effect=[
            MagicMock(content=json.dumps({"strategy": "temporal"})),
            MagicMock(
                content=json.dumps(
                    {
                        "claims": [
                            {
                                "id": "c0",
                                "text": ("JWST launched in December 2021."),
                            }
                        ],
                        "seed_queries": ["JWST launch date"],
                    }
                )
            ),
        ]
    )
    monkeypatch.setattr(planner_nodes, "get_llm", lambda: planner_model)
    monkeypatch.setattr(
        planner_nodes_base,
        "get_llm",
        lambda: planner_model,
    )
    searcher_agent.reset_agent_cache()
    monkeypatch.setattr(
        searcher_agent,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "queries_used": ["JWST launch date"],
                "hits": [
                    {
                        "url": "https://nasa.example/jwst",
                        "title": "NASA JWST",
                        "snippet": "launched 2021",
                        "source": "tavily",
                        "score": 0.9,
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(
        searcher_core,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "queries_used": ["JWST launch date"],
                "hits": [
                    {
                        "url": "https://nasa.example/jwst",
                        "title": "NASA JWST",
                        "snippet": "launched 2021",
                        "source": "tavily",
                        "score": 0.9,
                    }
                ],
            }
        ),
    )
    reader_agent.reset_agent_cache()
    monkeypatch.setattr(
        reader_agent,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "pages": [
                    {
                        "url": "https://nasa.example/jwst",
                        "title": "NASA JWST",
                        "markdown": (
                            "# NASA\n\nJWST launched December 25, 2021."
                        ),
                        "word_count": 6,
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        reader_core,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "pages": [
                    {
                        "url": "https://nasa.example/jwst",
                        "title": "NASA JWST",
                        "markdown": (
                            "# NASA\n\nJWST launched December 25, 2021."
                        ),
                        "word_count": 6,
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(
        fc_verify,
        "get_llm",
        lambda: _llm_stub(
            {
                "verified_claims": [
                    {
                        "id": "c0",
                        "text": ("JWST launched in December 2021."),
                        "verdict": "SUPPORTED",
                        "confidence": 0.95,
                        "sources": ["https://nasa.example/jwst"],
                    }
                ],
                "follow_up_queries": [],
            }
        ),
    )
    synth_agent.reset_agent_cache()
    monkeypatch.setattr(
        synth_agent,
        "build_agent",
        lambda: _FakePydAgent(
            ReportOutput(
                title="JWST Launch",
                summary="JWST launched in December 2021.",
                sections=[],
            )
        ),
    )
