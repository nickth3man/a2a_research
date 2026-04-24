"""Shared helpers for workflow integration tests."""

from __future__ import annotations

from typing import Any

import pytest

from a2a_research.backend.agents.langgraph.fact_checker import (
    main as fact_checker_main,
)
from a2a_research.backend.agents.pocketflow.planner import main as planner_main
from a2a_research.backend.agents.pydantic_ai.synthesizer import (
    main as synth_main,
)
from a2a_research.backend.agents.smolagents.reader import main as reader_main
from a2a_research.backend.agents.smolagents.searcher import (
    main as searcher_main,
)
from a2a_research.backend.core.a2a.registry import AgentRegistry
from tests.http_harness import make_multi_app_client


def _apps() -> dict[str, object]:
    from fastapi import FastAPI

    from a2a_research.backend.entrypoints.agent_mounts import (
        mount_agents,
    )

    # Individual agent apps for card serving
    apps = {
        "http://localhost:10001": (planner_main.build_http_app()),
        "http://localhost:10002": (searcher_main.build_http_app()),
        "http://localhost:10003": (reader_main.build_http_app()),
        "http://localhost:10004": (fact_checker_main.build_http_app()),
        "http://localhost:10005": (synth_main.build_http_app()),
    }

    # Unified gateway for message routing
    gateway = FastAPI()
    mount_agents(gateway)
    apps["http://localhost:8000"] = gateway

    return apps


def _install_http_services(
    monkeypatch: pytest.MonkeyPatch,
) -> Any:
    from a2a_research.backend.core.a2a import (
        client as client_mod,
    )
    from a2a_research.backend.core.settings import settings

    shared_client = make_multi_app_client(_apps())

    # Patch settings to use trailing slashes for mount compatibility
    monkeypatch.setattr(
        settings, "planner_url", "http://localhost:8000/agents/planner/"
    )
    monkeypatch.setattr(
        settings, "searcher_url", "http://localhost:8000/agents/searcher/"
    )
    monkeypatch.setattr(
        settings, "reader_url", "http://localhost:8000/agents/reader/"
    )
    monkeypatch.setattr(
        settings,
        "fact_checker_url",
        "http://localhost:8000/agents/fact-checker/",
    )
    monkeypatch.setattr(
        settings,
        "synthesizer_url",
        "http://localhost:8000/agents/synthesizer/",
    )

    # Rebuild agent cards with patched URLs
    import a2a_research.backend.core.a2a.cards as cards_mod

    monkeypatch.setattr(cards_mod, "AGENT_CARDS", cards_mod.build_cards())

    registry = AgentRegistry(
        planner_url="http://localhost:8000/agents/planner/",
        searcher_url="http://localhost:8000/agents/searcher/",
        reader_url="http://localhost:8000/agents/reader/",
        fact_checker_url=("http://localhost:8000/agents/fact-checker/"),
        synthesizer_url=("http://localhost:8000/agents/synthesizer/"),
    )

    def _client_factory(*a: object, **kw: object) -> Any:
        return shared_client

    monkeypatch.setattr(client_mod.httpx, "AsyncClient", _client_factory)
    monkeypatch.setattr(client_mod, "get_registry", lambda: registry)

    import a2a_research.backend.core.a2a as a2a_mod

    monkeypatch.setattr(a2a_mod, "get_registry", lambda: registry)

    return shared_client
