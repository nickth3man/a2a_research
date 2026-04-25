"""Static AgentCard for the Synthesizer HTTP service."""

from __future__ import annotations

from core import AgentRole, get_card

SYNTHESIZER_CARD = get_card(AgentRole.SYNTHESIZER)

__all__ = ["SYNTHESIZER_CARD"]
