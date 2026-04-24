"""Static AgentCard for the Reader HTTP service."""

from __future__ import annotations

from a2a_research.backend.core.a2a.cards import get_card
from a2a_research.backend.core.models import AgentRole

READER_CARD = get_card(AgentRole.READER)

__all__ = ["READER_CARD"]
