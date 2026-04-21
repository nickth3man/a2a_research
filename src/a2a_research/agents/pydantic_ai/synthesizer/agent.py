"""Pydantic AI agent factory for the Synthesizer.

Env vars consumed (via :data:`settings.llm`):
``LLM_MODEL``, ``LLM_BASE_URL``, ``LLM_API_KEY`` — aligned with the
OpenRouter-backed provider used by Planner/FactChecker.
"""

from __future__ import annotations

from functools import lru_cache
from typing import cast

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from a2a_research.agents.pydantic_ai.synthesizer.prompt import (
    SYNTHESIZER_PROMPT,
)
from a2a_research.models import ReportOutput
from a2a_research.settings import settings

__all__ = ["build_agent", "build_model", "reset_agent_cache"]


def build_model() -> OpenAIChatModel:
    """Return the OpenRouter-backed pydantic-ai model."""
    return OpenAIChatModel(
        settings.llm.model,
        provider=OpenAIProvider(
            base_url=settings.llm.base_url, api_key=settings.llm.api_key
        ),
    )


@lru_cache(maxsize=1)
def build_agent() -> Agent[None, ReportOutput]:
    """Return a cached ``Agent`` with :class:`ReportOutput` as structured"""
    """output."""
    return cast(
        "Agent[None, ReportOutput]",
        Agent(
            build_model(),
            instructions=SYNTHESIZER_PROMPT,
            output_type=ReportOutput,
            # Default retries=1 is tight for schema-shaped JSON; extra attempts
            # reduce flaky failures.
            output_retries=4,
        ),
    )


def reset_agent_cache() -> None:
    build_agent.cache_clear()
