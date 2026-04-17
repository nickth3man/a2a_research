"""smolagents ``ToolCallingAgent`` factory for the Reader role."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from smolagents import OpenAIServerModel, ToolCallingAgent

from a2a_research.agents.smolagents.reader.prompt import READER_PROMPT
from a2a_research.agents.smolagents.reader.tools import FetchAndExtractTool
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
        tools=[FetchAndExtractTool()],
        model=build_model(),
        instructions=READER_PROMPT,
        max_steps=5,
        verbosity_level=0,
        max_tool_threads=4,
    )


def reset_agent_cache() -> None:
    build_agent.cache_clear()
