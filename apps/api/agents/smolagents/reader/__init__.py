"""Reader — smolagents ToolCallingAgent wrapping trafilatura fetch +
extract."""

from __future__ import annotations

from agents.smolagents.reader.agent import build_agent
from agents.smolagents.reader.main import ReaderExecutor

__all__ = ["ReaderExecutor", "build_agent"]
