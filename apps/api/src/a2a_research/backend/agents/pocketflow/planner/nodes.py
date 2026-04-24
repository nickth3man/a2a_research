"""PocketFlow nodes for the Planner."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncNode

from a2a_research.backend.agents.pocketflow.planner.nodes_base import (
    CLASSIFIER_PROMPT,
    COMPARATIVE_PROMPT,
    FACTUAL_PROMPT,
    TEMPORAL_PROMPT,
    _BaseDecomposeNode,
)
from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.models import AgentRole, Claim
from a2a_research.backend.core.progress import emit_llm_response, emit_prompt
from a2a_research.backend.core.settings import settings
from a2a_research.backend.llm.providers import ProviderRequestError, get_llm

logger = get_logger(__name__)

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

    async def post_async(
        self, shared: dict[str, Any], prep_res: None, exec_res: None
    ) -> str:
        return "done"


class ClassifyNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> str:
        query = str(shared.get("query") or "").strip()
        if not query:
            raise ValueError("Planner shared store missing non-empty 'query'.")
        return query

    async def exec_async(self, prep_res: str) -> dict[str, str]:
        from time import perf_counter

        from a2a_research.backend.agents.pocketflow.planner.nodes_base import (
            _heuristic_strategy,
        )

        query = prep_res
        emit_prompt(
            AgentRole.PLANNER,
            "classify",
            query,
            system_text=CLASSIFIER_PROMPT,
            model=settings.llm.model,
        )
        started = perf_counter()
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
        emit_llm_response(
            AgentRole.PLANNER,
            "classify",
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )

        from a2a_research.backend.core.utils.json_utils import (
            parse_json_safely,
        )

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


class FactualDecomposeNode(_BaseDecomposeNode):
    prompt = FACTUAL_PROMPT


class ComparativeDecomposeNode(_BaseDecomposeNode):
    prompt = COMPARATIVE_PROMPT


class TemporalDecomposeNode(_BaseDecomposeNode):
    prompt = TEMPORAL_PROMPT


class SeedQueryNode(AsyncNode):
    async def prep_async(
        self, shared: dict[str, Any]
    ) -> tuple[str, list[Claim], list[str]]:
        return (
            str(shared.get("query") or "").strip(),
            list(shared.get("claims") or []),
            list(shared.get("seed_queries") or []),
        )

    async def exec_async(
        self, prep_res: tuple[str, list[Claim], list[str]]
    ) -> list[str]:
        query, claims, existing = prep_res
        if existing:
            return existing
        seed_queries = [
            claim.text for claim in claims[:3] if claim.text.strip()
        ]
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
        from a2a_research.backend.agents.pocketflow.planner.nodes_base import (
            _build_default_dag,
            _infer_freshness,
        )

        query = prep_res
        claim = Claim(
            id="c0",
            text=query or "No query provided.",
            freshness=_infer_freshness(query),
        )
        return {
            "claims": [claim],
            "claim_dag": _build_default_dag([claim]),
            "seed_queries": [query] if query else [],
        }

    async def post_async(
        self, shared: dict[str, Any], prep_res: str, exec_res: dict[str, Any]
    ) -> str:
        shared["claims"] = exec_res["claims"]
        shared["claim_dag"] = exec_res["claim_dag"]
        shared["seed_queries"] = exec_res["seed_queries"]
        return "default"
