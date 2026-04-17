"""LangGraph StateGraph that implements the FactChecker loop.

Linear first pass, then conditional loop-back based on :func:`route`:

    START → ask_searcher → ask_reader → verify →
        (continue?) → ask_searcher → ...
        (done?) → END
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from a2a_research.agents.langgraph.fact_checker.nodes import (
    build_ask_reader_node,
    build_ask_searcher_node,
    build_verify_node,
    route,
)
from a2a_research.agents.langgraph.fact_checker.state import FactCheckState

__all__ = ["build_fact_check_graph"]


def build_fact_check_graph(client: Any) -> Any:
    """Compile the FactChecker graph, closing over an :class:`A2AClient`."""
    graph: StateGraph[FactCheckState, Any, Any, Any] = StateGraph(FactCheckState)
    graph.add_node("ask_searcher", build_ask_searcher_node(client))
    graph.add_node("ask_reader", build_ask_reader_node(client))
    graph.add_node("verify", build_verify_node())

    graph.add_edge(START, "ask_searcher")
    graph.add_edge("ask_searcher", "ask_reader")
    graph.add_edge("ask_reader", "verify")
    graph.add_conditional_edges("verify", route, {"continue": "ask_searcher", "done": END})
    return graph.compile()
