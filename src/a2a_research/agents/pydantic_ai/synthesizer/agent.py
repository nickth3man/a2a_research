"""Pydantic AI agent factory for the Synthesizer.

Env vars consumed (via :data:`settings.llm`):
``LLM_MODEL`` → model_name, ``LLM_BASE_URL`` → provider.base_url,
``LLM_API_KEY`` → provider.api_key.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, cast

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from a2a_research.agents.pydantic_ai.synthesizer.prompt import SYNTHESIZER_PROMPT
from a2a_research.models import ReportOutput
from a2a_research.settings import settings

__all__ = ["build_agent", "build_model", "reset_agent_cache"]


def build_model() -> OpenAIChatModel:
    provider_kwargs: dict[str, Any] = {}
    if settings.llm.base_url:
        provider_kwargs["base_url"] = settings.llm.base_url
    if settings.llm.api_key:
        provider_kwargs["api_key"] = settings.llm.api_key
    provider = OpenAIProvider(**provider_kwargs)
    return OpenAIChatModel(settings.llm.model, provider=provider)


@lru_cache(maxsize=1)
def build_agent() -> Agent[None, ReportOutput]:
    """Return a cached ``Agent`` with :class:`ReportOutput` as structured output."""
    return cast(
        "Agent[None, ReportOutput]",
        Agent(build_model(), instructions=SYNTHESIZER_PROMPT, output_type=ReportOutput),
    )


def reset_agent_cache() -> None:
    build_agent.cache_clear()
