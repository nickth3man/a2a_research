"""Top-level research workflow orchestrator.

Linear hand-off: Planner → FactChecker (internal team loop) → Synthesizer.
"""

from __future__ import annotations

from a2a_research.workflow.coordinator import (
    run_research,
    run_research_async,
    run_research_sync,
)

__all__ = ["run_research", "run_research_async", "run_research_sync"]
