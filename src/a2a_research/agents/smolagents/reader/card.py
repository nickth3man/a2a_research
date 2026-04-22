"""Static AgentCard for the Reader HTTP service."""

from __future__ import annotations

from a2a_research.a2a.cards import get_card
from a2a_research.models import AgentRole

READER_CARD = get_card(AgentRole.READER)

__all__ = ["READER_CARD"]
