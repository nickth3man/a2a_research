"""Clarifier flow tests with LLM mocked."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.pocketflow.clarifier import clarify
from agents.pocketflow.clarifier import (
    nodes as clarifier_nodes,
)


def _mock_llm(response_payload: dict[str, Any]) -> Any:
    model = MagicMock()

    async def ainvoke(messages: list[dict[str, str]]) -> Any:
        return MagicMock(content=json.dumps(response_payload))

    model.ainvoke = AsyncMock(side_effect=ainvoke)
    return model


@pytest.mark.asyncio
async def test_clarify_factual_query_returns_passthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(clarifier_nodes, "get_llm", lambda: _mock_llm({}))

    result = await clarify("What is the speed of light?")
    assert result["committed_interpretation"] == "What is the speed of light?"
    assert result["disambiguations"] == []
    assert "unambiguous" in result["audit_note"]


@pytest.mark.asyncio
async def test_clarify_ambiguous_query_returns_disambiguations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        clarifier_nodes,
        "get_llm",
        lambda: _mock_llm(
            {
                "disambiguations": [
                    {"interpretation": "Speed in vacuum", "confidence": 0.9}
                ],
                "committed_interpretation": "Speed in vacuum",
                "needs_disambiguation": True,
            }
        ),
    )

    result = await clarify(
        "What is the speed of light?", query_class="ambiguous"
    )
    assert result["committed_interpretation"] == "Speed in vacuum"
    assert len(result["disambiguations"]) == 1
    assert result["disambiguations"][0]["interpretation"] == "Speed in vacuum"
