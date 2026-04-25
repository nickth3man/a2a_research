"""Shared fixtures for integration tests.

Provides an ``async_client`` fixture backed by the FastAPI app's ASGI
transport so integration tests can exercise the full request/response
cycle without a running server.

Usage::

    async def test_health(async_client):
        resp = await async_client.get("/api/health")
        assert resp.status_code == 200
"""

from __future__ import annotations

import httpx
import pytest


@pytest.fixture
async def async_client():
    """Yield an :class:`httpx.AsyncClient` wired to the FastAPI app via ASGI.

    The client uses :class:`httpx.ASGITransport` so all requests are handled
    in-process — no network socket is opened.  The client is automatically
    closed after the test.

    Example::

        async def test_start_research(async_client):
            resp = await async_client.post(
                "/api/research",
                json={"query": "test query"},
            )
            assert resp.status_code == 200
            session_id = resp.json()["session_id"]
    """
    from entrypoints import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=30.0,
    ) as client:
        yield client
