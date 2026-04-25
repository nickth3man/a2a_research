"""Five framework-specific research agents.

Each role lives in a subpackage named after its framework + role:

- :mod:`a2a_research.agents.pocketflow.planner` — query decomposition
- :mod:`a2a_research.agents.smolagents.searcher` — parallel web search
- :mod:`a2a_research.agents.smolagents.reader` — URL fetch + extraction
- :mod:`a2a_research.agents.langgraph.fact_checker` — bounded verification loop
- :mod:`a2a_research.agents.pydantic_ai.synthesizer` — structured report

Each subpackage exposes an ``AgentExecutor`` subclass that plugs into the
in-process A2A registry in :mod:`a2a_research.a2a`.
"""

from __future__ import annotations

__all__: list[str] = []
