"""Shared helpers for workflow integration tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from a2a_research.a2a.registry import AgentRegistry
from a2a_research.agents.langgraph.fact_checker import (
    main as fact_checker_main,
    verify_route as fc_verify,
)
from a2a_research.agents.pocketflow.planner import main as planner_main
from a2a_research.agents.pocketflow.planner import nodes as planner_nodes
from a2a_research.agents.pydantic_ai.synthesizer import agent as synth_agent
from a2a_research.agents.pydantic_ai.synthesizer import main as synth_main
from a2a_research.agents.smolagents.reader import (
    core as reader_core, main as reader_main)
from a2a_research.agents.smolagents.searcher import (
    core as searcher_core, main as searcher_main)
from a2a_research.models import ReportOutput
from tests.http_harness import make_multi_app_client


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


def _apps() -> dict[str, object]:
    return {
        "http://localhost:10001": planner_main.build_http_app(),
        "http://localhost:10002": searcher_main.build_http_app(),
        "http://localhost:10003": reader_main.build_http_app(),
        "http://localhost:10004": fact_checker_main.build_http_app(),
        "http://localhost:10005": synth_main.build_http_app(),
    }


def _configure_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
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
                                "text": "JWST launched in December 2021.",
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
                        "text": "JWST launched in December 2021.",
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


def _install_http_services(monkeypatch: pytest.MonkeyPatch) -> Any:
    from a2a_research.a2a import client as client_module
    from a2a_research.workflow import coordinator as coordinator_module

    shared_client = make_multi_app_client(_apps())
    registry = AgentRegistry()

    def _client_factory(*args: object, **kwargs: object) -> Any:
        return shared_client

    monkeypatch.setattr(client_module.httpx, "AsyncClient", _client_factory)
    monkeypatch.setattr(client_module, "get_registry", lambda: registry)
    import a2a_research.a2a as a2a_module

    monkeypatch.setattr(a2a_module, "get_registry", lambda: registry)
    return shared_client
