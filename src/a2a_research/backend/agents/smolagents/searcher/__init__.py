"""Searcher — smolagents ToolCallingAgent wrapping the parallel web search"""

from __future__ import annotations

from a2a_research.backend.agents.smolagents.searcher.agent import build_agent
from a2a_research.backend.agents.smolagents.searcher.main import (
    SearcherExecutor,
)

__all__ = ["SearcherExecutor", "build_agent"]
