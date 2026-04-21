"""Terminal node for the Clarifier."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncNode


class TerminalNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> None:
        return None

    async def exec_async(self, prep_res: None) -> None:
        return None

    async def post_async(
        self, shared: dict[str, Any], prep_res: None, exec_res: None
    ) -> str:
        return "done"
