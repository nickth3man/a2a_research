"""Synthesizer — typed report writer built on :class:`pydantic_ai.Agent`."""

from __future__ import annotations

from agents.pydantic_ai.synthesizer.agent import (
    build_agent,
)
from agents.pydantic_ai.synthesizer.main import (
    SynthesizerExecutor,
    synthesize,
)

__all__ = ["SynthesizerExecutor", "build_agent", "synthesize"]
