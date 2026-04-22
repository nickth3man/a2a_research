"""Static AgentCard for the Planner HTTP service."""

from __future__ import annotations

from a2a_research.backend.core.a2a.cards import get_card
from a2a_research.backend.core.models import AgentRole

PLANNER_CARD = get_card(AgentRole.PLANNER)

__all__ = ["PLANNER_CARD"]
