"""In-process A2A layer built on the official ``a2a-sdk`` protocol types.

Public surface:
- :func:`get_registry` — lazily builds the five-agent :class:`AgentRegistry`.
- :class:`A2AClient` — sends a :class:`Message` to a registered role, returns the final Task.
- :func:`build_message`, :func:`extract_data_payloads`, :func:`extract_text` — helpers.
- :data:`AGENT_CARDS` — per-role :class:`AgentCard` for discovery and UI labels.
"""

from __future__ import annotations

from a2a_research.a2a.cards import AGENT_CARDS, get_card
from a2a_research.a2a.client import (
    A2AClient,
    build_message,
    extract_data_payloads,
    extract_text,
)
from a2a_research.a2a.registry import (
    AgentRegistry,
    get_registry,
    register_executor,
    register_executor_factory,
    reset_registry,
)

__all__ = [
    "AGENT_CARDS",
    "A2AClient",
    "AgentRegistry",
    "build_message",
    "extract_data_payloads",
    "extract_text",
    "get_card",
    "get_registry",
    "register_executor",
    "register_executor_factory",
    "reset_registry",
]
