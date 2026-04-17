"""AgentCard re-export for the Planner role."""

from __future__ import annotations

from a2a_research.a2a.cards import get_card
from a2a_research.models import AgentRole

PLANNER_CARD = get_card(AgentRole.PLANNER)

__all__ = ["PLANNER_CARD"]
