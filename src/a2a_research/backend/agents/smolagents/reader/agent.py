"""smolagents ``ToolCallingAgent`` factory for the Reader role."""

from __future__ import annotations

from functools import lru_cache

from smolagents import OpenAIServerModel, ToolCallingAgent

from a2a_research.backend.agents.smolagents.reader.prompt import READER_PROMPT
from a2a_research.backend.agents.smolagents.reader.tools import (
    FetchAndExtractTool,
)
from a2a_research.backend.agents.smolagents.searcher.agent import (
    _smolagents_step_callback,
)
from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.settings import settings

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
        tools=[FetchAndExtractTool()],
        model=build_model(),
        instructions=READER_PROMPT,
        max_steps=5,
        verbosity_level=0,
        max_tool_threads=4,
        step_callbacks=[_smolagents_step_callback(AgentRole.READER)],
    )


def reset_agent_cache() -> None:
    build_agent.cache_clear()
