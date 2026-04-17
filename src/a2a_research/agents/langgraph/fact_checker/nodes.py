"""Node callables for the FactChecker langgraph.

The loop dispatches A2A messages to the Searcher and Reader (peer agents),
accumulates evidence, then has the LLM verify each claim. The router decides
whether to iterate again or hand off to the Synthesizer.

Error handling is explicit: if the Searcher or Reader surface provider-level
errors (e.g. Tavily disabled, DDG rate-limited, all URL fetches failed) the
errors are captured in ``state["errors"]``. If the search layer is exhausted
and we have no evidence, ``verify_node`` short-circuits to
``INSUFFICIENT_EVIDENCE`` verdicts whose ``evidence_snippets`` carry the
exact reason, and the router terminates the loop — no LLM guessing.
"""

from __future__ import annotations

from a2a_research.agents.langgraph.fact_checker.search_reader_nodes import (
    build_ask_reader_node,
    build_ask_searcher_node,
)
from a2a_research.agents.langgraph.fact_checker.verify_route import (
    build_verify_node,
    route,
)

__all__ = [
    "build_ask_reader_node",
    "build_ask_searcher_node",
    "build_verify_node",
    "route",
]
