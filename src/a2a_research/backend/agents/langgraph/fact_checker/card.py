"""Static AgentCard for the FactChecker HTTP service."""

from __future__ import annotations

from a2a_research.backend.core.a2a.cards import get_card
from a2a_research.backend.core.models import AgentRole

FACT_CHECKER_CARD = get_card(AgentRole.FACT_CHECKER)

__all__ = ["FACT_CHECKER_CARD"]
