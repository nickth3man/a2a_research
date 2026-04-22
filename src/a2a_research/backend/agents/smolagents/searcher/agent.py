"""smolagents ``ToolCallingAgent`` factory for the Searcher role.

Used by the standalone
``python -m a2a_research.agents.smolagents.searcher`` demo. The A2A
:class:`SearcherExecutor` calls :func:`a2a_research.tools.web_search` directly
for batch efficiency — see the note in ``main.py``.

Env vars: ``LLM_MODEL``, ``LLM_BASE_URL``, ``LLM_API_KEY`` via
:data:`settings.llm`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from smolagents import OpenAIServerModel, ToolCallingAgent

from a2a_research.backend.agents.smolagents.searcher.prompt import (
    SEARCHER_PROMPT,
)
from a2a_research.backend.agents.smolagents.searcher.tools import WebSearchTool
from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.progress import emit_tool_call
from a2a_research.backend.core.settings import settings

__all__ = ["build_agent", "build_model", "reset_agent_cache"]


def _smolagents_step_callback(role: AgentRole) -> Any:
    def _callback(step: Any, agent: Any | None = None) -> None:
        tool_calls = getattr(step, "tool_calls", None) or []
        for call in tool_calls:
            name = (
                getattr(call, "name", None)
                or getattr(call, "tool_name", "")
                or "?"
            )
            args = getattr(call, "arguments", None)
            if args is None:
                args = getattr(call, "args", None)
            observation = getattr(step, "observations", None) or getattr(
                step, "tool_call_output", ""
            )
            error = getattr(step, "error", None)
            emit_tool_call(
                role,
                str(name),
                args_preview=str(args)[:300] if args is not None else "",
                result_preview=str(observation)[:400] if observation else "",
                status=("error: " + str(error)) if error else "ok",
            )

    return _callback


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
        step_callbacks=[_smolagents_step_callback(AgentRole.SEARCHER)],
    )


def reset_agent_cache() -> None:
    build_agent.cache_clear()
