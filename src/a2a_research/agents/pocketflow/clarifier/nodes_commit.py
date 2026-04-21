"""Commit node for the Clarifier."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncNode


class CommitNode(AsyncNode):
    async def prep_async(
        self, shared: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], str, str]:
        disambiguations = list(shared.get("disambiguations") or [])
        committed = str(
            shared.get("committed_interpretation") or shared.get("query") or ""
        ).strip()
        query = str(shared.get("query") or "").strip()
        return disambiguations, committed, query

    async def exec_async(
        self, prep_res: tuple[list[dict[str, Any]], str, str]
    ) -> dict[str, Any]:
        disambiguations, committed, query = prep_res
        if not disambiguations:
            return {
                "committed_interpretation": committed or query,
                "confidence": 1.0,
            }
        if not committed:
            best = max(disambiguations, key=lambda d: d.get("confidence", 0.0))
            committed = best["interpretation"]
        return {"committed_interpretation": committed, "confidence": 1.0}

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: tuple[list[dict[str, Any]], str, str],
        exec_res: dict[str, Any],
    ) -> str:
        shared["committed_interpretation"] = exec_res[
            "committed_interpretation"
        ]
        return "default"
