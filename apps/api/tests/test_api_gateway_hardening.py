"""Tests for FastAPI gateway boundary hardening."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from entrypoints import api


def test_research_request_rejects_empty_query() -> None:
    with pytest.raises(ValidationError):
        api.ResearchRequest(query="")


def test_research_request_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        api.ResearchRequest(query="   ")


def test_research_request_strips_query() -> None:
    request = api.ResearchRequest(query="  what changed?  ")
    assert request.query == "what changed?"


def test_research_request_rejects_oversized_query() -> None:
    with pytest.raises(ValidationError):
        api.ResearchRequest(query="x" * 2001)


@pytest.mark.asyncio
async def test_require_api_key_allows_dev_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api.settings, "api_key", "")
    await api.require_api_key(None)


@pytest.mark.asyncio
async def test_require_api_key_rejects_wrong_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api.settings, "api_key", "expected")
    with pytest.raises(HTTPException) as exc_info:
        await api.require_api_key("wrong")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_accepts_matching_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api.settings, "api_key", "expected")
    await api.require_api_key("expected")


@pytest.mark.asyncio
async def test_require_api_key_accepts_query_key_for_sse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(api.settings, "api_key", "expected")
    await api.require_api_key(None, "expected")


def test_health_endpoint() -> None:
    client = TestClient(api.app)
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@patch("entrypoints.api.get_session_task", return_value=None)
def test_research_stream_unknown_session_returns_404(_m_task: object) -> None:
    client = TestClient(api.app)
    res = client.get("/api/research/does-not-exist/stream")
    assert res.status_code == 404


@patch("entrypoints.api.running_session_count", return_value=1_000)
def test_research_start_returns_429_when_too_many_sessions(
    _m_count: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api.settings, "max_concurrent_sessions", 1)
    client = TestClient(api.app)
    res = client.post(
        "/api/research", json={"query": "A short research question?"}
    )
    assert res.status_code == 429


@patch("entrypoints.api.running_session_count", return_value=0)
@patch("workflow.engine.drive", new_callable=AsyncMock)
def test_research_start_returns_session_id(
    m_drive: AsyncMock, _m_count: object
) -> None:
    m_drive.return_value = None
    client = TestClient(api.app, raise_server_exceptions=True)
    res = client.post(
        "/api/research", json={"query": "A short research question?"}
    )
    assert res.status_code == 200
    body = res.json()
    assert "session_id" in body
    assert len(body["session_id"]) > 0
