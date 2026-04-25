"""Static AgentCard for the Searcher HTTP service."""

from __future__ import annotations

from core import AgentRole, get_card

SEARCHER_CARD = get_card(AgentRole.SEARCHER)

__all__ = ["SEARCHER_CARD"]
