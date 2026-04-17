"""PocketFlow nodes for the Planner.

One async node calls the LLM with :data:`PLANNER_PROMPT`, parses the JSON
response into ``{claims, seed_queries}``, and writes them onto the shared store.
A second node emits a fallback plan if the LLM call fails or returns unparseable
output (the downstream pipeline must always receive at least one claim).
"""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.planner.prompt import PLANNER_PROMPT
from a2a_research.app_logging import get_logger
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import Claim
from a2a_research.providers import ProviderRequestError, get_llm

logger = get_logger(__name__)

__all__ = ["DecomposeNode", "FallbackNode", "TerminalNode"]


class TerminalNode(AsyncNode):
    """No-op terminal node used as the ``default`` successor when decomposition succeeds.

    PocketFlow warns if a node has successors and returns an action with no
    match, so we give ``default`` an explicit endpoint even though the real
    state has already been written by ``DecomposeNode``.
    """

    async def prep_async(self, shared: dict[str, Any]) -> None:
        return None

    async def exec_async(self, prep_res: None) -> None:
        return None

    async def post_async(self, shared: dict[str, Any], prep_res: None, exec_res: None) -> str:
        return "done"


class DecomposeNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> str:
        query = str(shared.get("query") or "").strip()
        if not query:
            raise ValueError("Planner shared store missing non-empty 'query'.")
        return query

    async def exec_async(self, prep_res: str) -> dict[str, Any]:
        query = prep_res
        logger.info("Planner decomposing query=%r", query)
        try:
            model = get_llm()
            response = model.invoke(
                [
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": query},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning("Planner LLM failed: %s", exc)
            return {"raw": "", "error": str(exc)}
        return {"raw": raw, "error": None}

    async def post_async(
        self, shared: dict[str, Any], prep_res: str, exec_res: dict[str, Any]
    ) -> str:
        shared["raw"] = exec_res.get("raw") or ""
        shared["error"] = exec_res.get("error")
        data = parse_json_safely(shared["raw"])
        claims, seed_queries = _extract(data)
        if not claims:
            shared["claims"] = []
            shared["seed_queries"] = []
            return "fallback"
        shared["claims"] = claims
        shared["seed_queries"] = seed_queries or [prep_res]
        return "default"


class FallbackNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> str:
        return str(shared.get("query") or "")

    async def exec_async(self, prep_res: str) -> dict[str, Any]:
        query = prep_res
        claim = Claim(id="c0", text=query or "No query provided.")
        return {"claims": [claim], "seed_queries": [query] if query else []}

    async def post_async(
        self, shared: dict[str, Any], prep_res: str, exec_res: dict[str, Any]
    ) -> str:
        shared["claims"] = exec_res["claims"]
        shared["seed_queries"] = exec_res["seed_queries"]
        return "default"


def _extract(data: dict[str, Any] | None) -> tuple[list[Claim], list[str]]:
    if not isinstance(data, dict):
        return [], []
    claims: list[Claim] = []
    for i, item in enumerate(data.get("claims") or []):
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            raw_id = item.get("id") or f"c{i}"
            claims.append(Claim(id=str(raw_id), text=text))
        elif isinstance(item, str) and item.strip():
            claims.append(Claim(id=f"c{i}", text=item.strip()))
    seeds_raw = data.get("seed_queries") or []
    seeds: list[str] = [str(s).strip() for s in seeds_raw if isinstance(s, str) and s.strip()]
    return claims, seeds
