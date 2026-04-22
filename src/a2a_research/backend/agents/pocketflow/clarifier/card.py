"""Static AgentCard for the Clarifier HTTP service."""

from __future__ import annotations

from a2a_research.backend.core.a2a.cards import get_card
from a2a_research.backend.core.models import AgentRole

CLARIFIER_CARD = get_card(AgentRole.CLARIFIER)

__all__ = ["CLARIFIER_CARD"]
