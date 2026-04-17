"""AgentCard re-export for the Synthesizer role."""

from __future__ import annotations

from a2a_research.a2a.cards import get_card
from a2a_research.models import AgentRole

SYNTHESIZER_CARD = get_card(AgentRole.SYNTHESIZER)

__all__ = ["SYNTHESIZER_CARD"]
