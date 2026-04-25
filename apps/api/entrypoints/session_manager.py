"""Session management for the FastAPI research gateway."""

from __future__ import annotations

from time import monotonic
from typing import TYPE_CHECKING

from core import Bus, settings

if TYPE_CHECKING:
    import asyncio

    from core import ResearchSession

_sessions: dict[str, asyncio.Task[ResearchSession]] = {}
_session_created_at: dict[str, float] = {}


def prune_expired_sessions() -> None:
    """Remove expired sessions and cancel their tasks."""
    now = monotonic()
    expired = [
        session_id
        for session_id, created_at in _session_created_at.items()
        if now - created_at > settings.session_ttl_seconds
    ]
    for session_id in expired:
        task = _sessions.pop(session_id, None)
        _session_created_at.pop(session_id, None)
        Bus.unregister(session_id)
        if task is not None and not task.done():
            task.cancel()


def running_session_count() -> int:
    """Return the number of active (non-done) sessions."""
    prune_expired_sessions()
    return sum(1 for task in _sessions.values() if not task.done())


def get_session_task(
    session_id: str,
) -> asyncio.Task[ResearchSession] | None:
    """Return the task for a session, or None if not found."""
    return _sessions.get(session_id)


def register_session(
    session_id: str,
    task: asyncio.Task[ResearchSession],
) -> None:
    """Register a new session and its task."""
    _sessions[session_id] = task
    _session_created_at[session_id] = monotonic()


def unregister_session(session_id: str) -> None:
    """Remove a session from tracking."""
    _sessions.pop(session_id, None)
    _session_created_at.pop(session_id, None)
    Bus.unregister(session_id)
