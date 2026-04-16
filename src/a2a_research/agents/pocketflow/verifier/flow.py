"""Single-node :class:`~pocketflow.AsyncFlow` wrapping just the Verifier."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncFlow

from .nodes import create_node


def build_flow() -> AsyncFlow[Any, Any]:
    return AsyncFlow(start=create_node())
