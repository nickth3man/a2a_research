"""FactChecker — bounded LangGraph loop that verifies claims.

Top-level workflow calls this service over HTTP once per run; internally the
graph dispatches Searcher and Reader via A2A (see ``graph`` and
``search_reader_nodes`` in this package).
"""

from __future__ import annotations

from a2a_research.agents.langgraph.fact_checker.graph import build_fact_check_graph
from a2a_research.agents.langgraph.fact_checker.main import (
    FactCheckerExecutor,
    run_fact_check,
)
from a2a_research.agents.langgraph.fact_checker.state import FactCheckState

__all__ = [
    "FactCheckState",
    "FactCheckerExecutor",
    "build_fact_check_graph",
    "run_fact_check",
]
