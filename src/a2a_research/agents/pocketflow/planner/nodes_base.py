"""Base nodes and helpers for the Planner."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.planner.nodes_extract import (
    _build_default_dag,
    _extract,
    _extract_freshness,
    _heuristic_strategy,
    _infer_freshness,
)
from a2a_research.agents.pocketflow.planner.prompt import (
    CLASSIFIER_PROMPT,
    COMPARATIVE_PROMPT,
    FACTUAL_PROMPT,
    TEMPORAL_PROMPT,
)
from a2a_research.app_logging import get_logger
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import AgentRole
from a2a_research.progress import emit_llm_response, emit_prompt
from a2a_research.providers import ProviderRequestError, get_llm
from a2a_research.settings import settings

logger = get_logger(__name__)

__all__ = [
    "CLASSIFIER_PROMPT",
    "COMPARATIVE_PROMPT",
    "FACTUAL_PROMPT",
    "TEMPORAL_PROMPT",
    "_BaseDecomposeNode",
    "_build_default_dag",
    "_extract",
    "_extract_freshness",
    "_heuristic_strategy",
    "_infer_freshness",
]


class _BaseDecomposeNode(AsyncNode):
    prompt: str

    async def prep_async(self, shared: dict[str, Any]) -> str:
        return str(shared.get("query") or "").strip()

    async def exec_async(self, prep_res: str) -> dict[str, Any]:
        query = prep_res
        logger.info(
            "Planner decomposing strategy=%s query=%r",
            self.__class__.__name__,
            query,
        )
        name = self.__class__.__name__.removesuffix("DecomposeNode")
        label = f"decompose_{name.lower()}"
        emit_prompt(
            AgentRole.PLANNER,
            label,
            query,
            system_text=self.prompt,
            model=settings.llm.model,
        )
        started = perf_counter()
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
            logger.warning(
                "Planner LLM failed in %s: %s", self.__class__.__name__, exc
            )
            return {"raw": "", "error": str(exc)}
        emit_llm_response(
            AgentRole.PLANNER,
            label,
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )
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
        shared["claim_dag"] = _build_default_dag(claims)
        shared["seed_queries"] = seed_queries
        return "default"
