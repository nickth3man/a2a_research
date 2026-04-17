"""A2A Research — 5-agent web research system orchestrated via the A2A protocol.

Pipeline (in-process A2A, using ``a2a-sdk``):

    Planner (pocketflow)
      → FactChecker (langgraph StateGraph loop)
            ↔ Searcher (smolagents + Tavily + DuckDuckGo)
            ↔ Reader   (smolagents + trafilatura)
      → Synthesizer (pydantic_ai, structured ReportOutput)

Entrypoints:

- :func:`a2a_research.workflow.run_research_sync` — run the pipeline on a query.
- :mod:`a2a_research.ui.app` — Mesop web UI.
- :mod:`a2a_research.a2a` — registry + client for agent-to-agent dispatch.

Configuration is environment-driven; see ``a2a_research.settings`` and ``.env.example``.
"""

__version__ = "0.2.0"
