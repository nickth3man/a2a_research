"""Static AgentCard for the Clarifier HTTP service."""

from __future__ import annotations

from core import AgentRole, get_card

CLARIFIER_CARD = get_card(AgentRole.CLARIFIER)

__all__ = ["CLARIFIER_CARD"]
