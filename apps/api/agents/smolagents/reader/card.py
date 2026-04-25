"""Static AgentCard for the Reader HTTP service."""

from __future__ import annotations

from core import AgentRole, get_card

READER_CARD = get_card(AgentRole.READER)

__all__ = ["READER_CARD"]
