"""PocketFlow nodes for the Planner."""

from __future__ import annotations

from typing import Any, Literal

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.planner.prompt import (
    CLASSIFIER_PROMPT,
    COMPARATIVE_PROMPT,
    FACTUAL_PROMPT,
    TEMPORAL_PROMPT,
)
from a2a_research.app_logging import get_logger
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import Claim
from a2a_research.providers import ProviderRequestError, get_llm

logger = get_logger(__name__)

PlannerStrategy = Literal["factual", "comparative", "temporal", "fallback"]

__all__ = [
    "ClassifyNode",
    "ComparativeDecomposeNode",
    "FactualDecomposeNode",
    "FallbackNode",
    "SeedQueryNode",
    "TemporalDecomposeNode",
    "TerminalNode",
]


class TerminalNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> None:
        return None

    async def exec_async(self, prep_res: None) -> None:
        return None

    async def post_async(self, shared: dict[str, Any], prep_res: None, exec_res: None) -> str:
        return "done"


class ClassifyNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> str:
        query = str(shared.get("query") or "").strip()
        if not query:
            raise ValueError("Planner shared store missing non-empty 'query'.")
        return query

    async def exec_async(self, prep_res: str) -> dict[str, str]:
        query = prep_res
        try:
            model = get_llm()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": CLASSIFIER_PROMPT},
                    {"role": "user", "content": query},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError:
            return {"strategy": _heuristic_strategy(query)}

        data = parse_json_safely(raw)
        strategy = str((data or {}).get("strategy") or "").strip().lower()
        if strategy not in {"factual", "comparative", "temporal", "fallback"}:
            strategy = _heuristic_strategy(query)
        return {"strategy": strategy}

    async def post_async(
        self, shared: dict[str, Any], prep_res: str, exec_res: dict[str, str]
    ) -> str:
        strategy = exec_res["strategy"]
        shared["strategy"] = strategy
        return strategy


class _BaseDecomposeNode(AsyncNode):
    prompt: str

    async def prep_async(self, shared: dict[str, Any]) -> str:
        return str(shared.get("query") or "").strip()

    async def exec_async(self, prep_res: str) -> dict[str, Any]:
        query = prep_res
        logger.info("Planner decomposing strategy=%s query=%r", self.__class__.__name__, query)
        try:
            model = get_llm()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": self.prompt},
                    {"role": "user", "content": query},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning("Planner LLM failed in %s: %s", self.__class__.__name__, exc)
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
            return "fallback"
        shared["claims"] = claims
        shared["seed_queries"] = seed_queries
        return "default"


class FactualDecomposeNode(_BaseDecomposeNode):
    prompt = FACTUAL_PROMPT


class ComparativeDecomposeNode(_BaseDecomposeNode):
    prompt = COMPARATIVE_PROMPT


class TemporalDecomposeNode(_BaseDecomposeNode):
    prompt = TEMPORAL_PROMPT


class SeedQueryNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> tuple[str, list[Claim], list[str]]:
        return (
            str(shared.get("query") or "").strip(),
            list(shared.get("claims") or []),
            list(shared.get("seed_queries") or []),
        )

    async def exec_async(self, prep_res: tuple[str, list[Claim], list[str]]) -> list[str]:
        query, claims, existing = prep_res
        if existing:
            return existing
        seed_queries = [claim.text for claim in claims[:3] if claim.text.strip()]
        if not seed_queries and query:
            seed_queries = [query]
        return seed_queries

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: tuple[str, list[Claim], list[str]],
        exec_res: list[str],
    ) -> str:
        shared["seed_queries"] = exec_res
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


def _heuristic_strategy(query: str) -> PlannerStrategy:
    lowered = query.lower()
    if any(token in lowered for token in ("compare", "vs", "versus", "better", "difference")):
        return "comparative"
    if any(
        token in lowered
        for token in ("when", "timeline", "history", "date", "year", "launched", "before", "after")
    ):
        return "temporal"
    return "factual"


def _extract(data: dict[str, Any] | None) -> tuple[list[Claim], list[str]]:
    if not isinstance(data, dict):
        return [], []
    claims: list[Claim] = []
    raw_claims = data.get("claims") or []
    if isinstance(raw_claims, list):
        for index, item in enumerate(raw_claims):
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                raw_id = item.get("id") or f"c{index}"
                claims.append(Claim(id=str(raw_id), text=text))
            elif isinstance(item, str) and item.strip():
                claims.append(Claim(id=f"c{index}", text=item.strip()))

    raw_seeds = data.get("seed_queries") or []
    seeds: list[str] = []
    if isinstance(raw_seeds, list):
        seeds = [str(item).strip() for item in raw_seeds if isinstance(item, str) and item.strip()]
    return claims, seeds
