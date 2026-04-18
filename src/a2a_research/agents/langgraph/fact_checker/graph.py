"""LangGraph StateGraph that implements the FactChecker loop.

The coordinator calls the Fact Checker service once; this graph orchestrates
search → read → verify with shared ``FactCheckState``, invoking Searcher and
Reader over A2A from the node factories in ``search_reader_nodes``.

Linear first pass, then conditional loop-back based on :func:`route`:

    START → ask_searcher → ask_reader → verify →
        (continue?) → ask_searcher → ...
        (done?) → END
"""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from a2a_research.agents.langgraph.fact_checker.nodes import (
    build_ask_reader_node,
    build_ask_searcher_node,
    build_verify_node,
    route,
)
from a2a_research.agents.langgraph.fact_checker.state import FactCheckState

__all__ = ["build_fact_check_graph"]

_COMPILED_GRAPH: Any | None = None


def build_fact_check_graph(client: Any) -> Any:
    """Compile the FactChecker graph once; the client is passed via state."""
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        graph = StateGraph(cast("Any", FactCheckState))
        graph.add_node("ask_searcher", build_ask_searcher_node())
        graph.add_node("ask_reader", build_ask_reader_node())
        graph.add_node("verify", build_verify_node())

        graph.add_edge(START, "ask_searcher")
        graph.add_edge("ask_searcher", "ask_reader")
        graph.add_edge("ask_reader", "verify")
        graph.add_conditional_edges("verify", route, {"continue": "ask_searcher", "done": END})
        _COMPILED_GRAPH = graph.compile()
    return _COMPILED_GRAPH
