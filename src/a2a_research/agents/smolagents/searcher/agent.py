"""smolagents ``ToolCallingAgent`` factory for the Searcher role.

Used by the standalone ``python -m a2a_research.agents.smolagents.searcher``
demo. The A2A :class:`SearcherExecutor` calls :func:`a2a_research.tools.web_search`
directly for batch efficiency — see the note in ``main.py``.

Env vars: ``LLM_MODEL``, ``LLM_BASE_URL``, ``LLM_API_KEY`` via :data:`settings.llm`.
"""

from __future__ import annotations

from functools import lru_cache

from smolagents import OpenAIServerModel, ToolCallingAgent

from a2a_research.agents.smolagents.searcher.prompt import SEARCHER_PROMPT
from a2a_research.agents.smolagents.searcher.tools import WebSearchTool
from a2a_research.settings import settings

__all__ = ["build_agent", "build_model", "reset_agent_cache"]


def build_model() -> OpenAIServerModel:
    return OpenAIServerModel(
        model_id=settings.llm.model,
        api_base=settings.llm.base_url,
        api_key=settings.llm.api_key,
    )


@lru_cache(maxsize=1)
def build_agent() -> ToolCallingAgent:
    return ToolCallingAgent(
        tools=[WebSearchTool()],
        model=build_model(),
        instructions=SEARCHER_PROMPT,
        max_steps=settings.searcher_max_steps,
        verbosity_level=0,
    )


def reset_agent_cache() -> None:
    build_agent.cache_clear()
