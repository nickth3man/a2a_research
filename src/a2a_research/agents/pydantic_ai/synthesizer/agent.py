"""Pydantic AI agent factory for the Synthesizer.

Env vars consumed (via :data:`settings.llm`):
``LLM_PROVIDER``, ``LLM_MODEL``, ``LLM_BASE_URL``, ``LLM_API_KEY`` — aligned with
:class:`a2a_research.providers.LLMProvider` routing used by Planner/FactChecker.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any, cast

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from a2a_research.agents.pydantic_ai.synthesizer.prompt import SYNTHESIZER_PROMPT
from a2a_research.models import ReportOutput
from a2a_research.settings import settings

if TYPE_CHECKING:
    from pydantic_ai.models import Model

__all__ = ["build_agent", "build_model", "reset_agent_cache"]


def _openai_compatible_kwargs() -> dict[str, Any]:
    kw: dict[str, Any] = {}
    if settings.llm.base_url:
        kw["base_url"] = settings.llm.base_url
    if settings.llm.api_key:
        kw["api_key"] = settings.llm.api_key
    return kw


def build_model() -> Model:
    """Return a pydantic-ai :class:`Model` for the configured ``LLM_PROVIDER``."""
    name = settings.llm.provider.lower()
    mid = settings.llm.model
    if name in {"openai", "openrouter", "ollama"}:
        return OpenAIChatModel(mid, provider=OpenAIProvider(**_openai_compatible_kwargs()))
    if name == "anthropic":
        return AnthropicModel(
            mid,
            provider=AnthropicProvider(
                api_key=settings.llm.api_key or None,
                base_url=settings.llm.base_url or None,
            ),
        )
    if name == "google":
        return GoogleModel(
            mid,
            provider=GoogleProvider(
                api_key=settings.llm.api_key or None,
                base_url=settings.llm.base_url or None,
            ),
        )
    msg = f"Unknown LLM_PROVIDER for Synthesizer: {name!r}"
    raise ValueError(msg)


@lru_cache(maxsize=1)
def build_agent() -> Agent[None, ReportOutput]:
    """Return a cached ``Agent`` with :class:`ReportOutput` as structured output."""
    return cast(
        "Agent[None, ReportOutput]",
        Agent(build_model(), instructions=SYNTHESIZER_PROMPT, output_type=ReportOutput),
    )


def reset_agent_cache() -> None:
    build_agent.cache_clear()
