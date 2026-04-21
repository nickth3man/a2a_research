"""Progress bus and queue registry."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from a2a_research.progress_types import ProgressEvent, ProgressQueue

__all__ = ["Bus"]


class Bus:
    """In-process registry of per-session progress queues."""

    _queues: ClassVar[dict[str, "ProgressQueue"]] = {}
    _loops: ClassVar[dict[str, asyncio.AbstractEventLoop]] = {}

    @classmethod
    def register(cls, session_id: str, queue: "ProgressQueue") -> None:
        """Register a progress queue for a session."""
        cls._queues[session_id] = queue
        with suppress(RuntimeError):
            cls._loops[session_id] = asyncio.get_running_loop()

    @classmethod
    def get(cls, session_id: str) -> "ProgressQueue | None":
        """Get the progress queue for a session."""
        return cls._queues.get(session_id)

    @classmethod
    def get_loop(cls, session_id: str) -> "asyncio.AbstractEventLoop | None":
        """Get the event loop for a session."""
        return cls._loops.get(session_id)

    @classmethod
    def unregister(cls, session_id: str) -> None:
        """Unregister a session's progress queue."""
        cls._queues.pop(session_id, None)
        cls._loops.pop(session_id, None)
