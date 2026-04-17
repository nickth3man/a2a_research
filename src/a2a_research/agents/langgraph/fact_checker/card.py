"""AgentCard re-export for the FactChecker role."""

from __future__ import annotations

from a2a_research.a2a.cards import get_card
from a2a_research.models import AgentRole

FACT_CHECKER_CARD = get_card(AgentRole.FACT_CHECKER)

__all__ = ["FACT_CHECKER_CARD"]
