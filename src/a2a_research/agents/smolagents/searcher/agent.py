"""smolagents ``ToolCallingAgent`` factory for the Searcher role.

Used by the standalone ``python -m a2a_research.agents.smolagents.searcher``
demo. The A2A :class:`SearcherExecutor` calls :func:`a2a_research.tools.web_search`
directly for batch efficiency — see the note in ``main.py``.

Env vars: ``LLM_MODEL``, ``LLM_BASE_URL``, ``LLM_API_KEY`` via :data:`settings.llm`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from smolagents import OpenAIServerModel, ToolCallingAgent

from a2a_research.agents.smolagents.searcher.prompt import SEARCHER_PROMPT
from a2a_research.agents.smolagents.searcher.tools import WebSearchTool
from a2a_research.settings import settings

__all__ = ["build_agent", "build_model", "reset_agent_cache"]


def build_model() -> OpenAIServerModel:
    init_kwargs: dict[str, Any] = {"model_id": settings.llm.model}
    if settings.llm.base_url:
        init_kwargs["api_base"] = settings.llm.base_url
    if settings.llm.api_key:
        init_kwargs["api_key"] = settings.llm.api_key
    return OpenAIServerModel(**init_kwargs)


@lru_cache(maxsize=1)
def build_agent() -> ToolCallingAgent:
    return ToolCallingAgent(
        tools=[WebSearchTool()],
        model=build_model(),
        instructions=SEARCHER_PROMPT,
        max_steps=3,
        verbosity_level=0,
    )


def reset_agent_cache() -> None:
    build_agent.cache_clear()
