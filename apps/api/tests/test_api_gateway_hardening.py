"""Tests for FastAPI gateway boundary hardening."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from a2a_research.backend.entrypoints import api


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
