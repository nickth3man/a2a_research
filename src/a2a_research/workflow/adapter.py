"""Sync adapter wrapping the PocketFlow AsyncFlow for backward-compatible invoke()."""

from __future__ import annotations

import asyncio
from typing import Any

from ..models import ResearchSession, WorkflowState
from .builder import get_workflow


class SyncWorkflowAdapter:
    __slots__ = ("_flow", "_shared")

    def __init__(
        self,
        flow,
        shared: dict[str, Any],
    ) -> None:
        self._flow = flow
        self._shared = shared

    def invoke(self, state: WorkflowState) -> dict[str, Any]:
        session: ResearchSession = state.session
        shared = self._shared.copy()
        shared["session"] = session

        asyncio.run(self._flow.run_async(shared))

        return {
            "session": shared["session"],
            "messages": shared.get("messages", []),
            "current_agent": shared.get("current_agent"),
        }

    async def ainvoke(self, state: WorkflowState) -> dict[str, Any]:
        session: ResearchSession = state.session
        shared = self._shared.copy()
        shared["session"] = session

        await self._flow.run_async(shared)

        return {
            "session": shared["session"],
            "messages": shared.get("messages", []),
            "current_agent": shared.get("current_agent"),
        }

    async def run_async(self, shared: dict[str, Any]) -> None:
        await self._flow.run_async(shared)


def get_graph():
    flow, shared = get_workflow()
    return SyncWorkflowAdapter(flow, shared)
