"""Reader — smolagents ToolCallingAgent wrapping trafilatura fetch + extract."""

from __future__ import annotations

from a2a_research.agents.smolagents.reader.agent import build_agent
from a2a_research.agents.smolagents.reader.main import ReaderExecutor

__all__ = ["ReaderExecutor", "build_agent"]
