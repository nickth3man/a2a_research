"""Tests for entrypoints.session_manager."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import patch

import pytest

from core import ResearchSession, settings


@pytest.mark.asyncio
async def test_register_get_unregister_session_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from entrypoints import session_manager as sm

    async def work() -> ResearchSession:
        return ResearchSession(query="q")

    t = asyncio.create_task(work())
    await asyncio.wait_for(t, timeout=2.0)
    sid = f"unit-reg-{uuid.uuid4().hex[:8]}"
    sm.register_session(sid, t)
    try:
        assert sm.get_session_task(sid) is t
    finally:
        sm.unregister_session(sid)
        assert sm.get_session_task(sid) is None


@pytest.mark.asyncio
async def test_running_session_count_includes_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from entrypoints import session_manager as sm

    async def slow() -> ResearchSession:
        await asyncio.sleep(3600)
        return ResearchSession()

    t = asyncio.create_task(slow())
    sid = f"unit-run-{uuid.uuid4().hex[:8]}"
    sm.register_session(sid, t)
    try:
        n = sm.running_session_count()
        assert n >= 1
    finally:
        t.cancel()
        await asyncio.gather(t, return_exceptions=True)
        sm.unregister_session(sid)


@pytest.mark.asyncio
async def test_prune_expired_removes_stale_and_cancels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from entrypoints import session_manager as sm

    monkeypatch.setattr(settings, "session_ttl_seconds", 1.0, raising=False)

    async def never() -> ResearchSession:
        await asyncio.sleep(99999)
        return ResearchSession()

    st_id = f"stale-{uuid.uuid4().hex[:8]}"
    with patch(
        "entrypoints.session_manager.monotonic", side_effect=[0.0, 100.0]
    ):
        t = asyncio.create_task(never())
        sm.register_session(st_id, t)
        sm.prune_expired_sessions()
    assert sm.get_session_task(st_id) is None
    await asyncio.gather(t, return_exceptions=True)
