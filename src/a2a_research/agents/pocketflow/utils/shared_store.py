"""Shared Store schema for the PocketFlow research pipeline.

PocketFlow's core abstraction pairs a directed graph with a Shared Store — a dict
that every node can read from (prep) and write to (post). Centralising the
contract here means any change to the dict's shape is visible in one place.

Schema keys
-----------

- ``session``           — :class:`~a2a_research.models.ResearchSession`
- ``messages``          — list of :class:`~a2a_research.models.A2AMessage` recorded by nodes
- ``current_agent``     — :class:`~a2a_research.models.AgentRole` or ``None``
- ``progress_reporter`` — optional callable injected by the UI to forward events
- ``progress_granularity`` — int granularity level for progress events (1..3)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from a2a_research.models import ResearchSession


def build_shared_store(session: ResearchSession | None = None) -> dict[str, Any]:
    """Return a freshly initialised Shared Store dict.

    Nodes rely on ``session`` and ``messages`` being present; callers may assign
    the session after construction when instantiating the workflow lazily.
    """
    return {
        "session": session,
        "messages": [],
        "current_agent": None,
    }
