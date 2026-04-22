"""Static AgentCard for the Searcher HTTP service."""

from __future__ import annotations

from a2a_research.a2a.cards import get_card
from a2a_research.models import AgentRole

SEARCHER_CARD = get_card(AgentRole.SEARCHER)

__all__ = ["SEARCHER_CARD"]
