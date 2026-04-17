"""Single-node :class:`~pocketflow.AsyncFlow` wrapping just the Researcher.

Intended for standalone invocation (tests, local debugging). The composed
pipeline lives in :mod:`a2a_research.agents.pocketflow.flow`.
"""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncFlow

from .nodes import create_node


def build_flow() -> AsyncFlow[Any, Any]:
    return AsyncFlow(start=create_node())
