"""FactChecker — bounded langgraph StateGraph loop that coordinates Searcher + Reader."""

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
