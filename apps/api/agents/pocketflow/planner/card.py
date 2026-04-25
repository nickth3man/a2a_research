"""Static AgentCard for the Planner HTTP service."""

from __future__ import annotations

from core import AgentRole, get_card

PLANNER_CARD = get_card(AgentRole.PLANNER)

__all__ = ["PLANNER_CARD"]
