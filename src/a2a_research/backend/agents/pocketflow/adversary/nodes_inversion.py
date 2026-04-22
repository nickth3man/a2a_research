"""PocketFlow nodes for the Adversary agent - Terminal and Inversion."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncNode

from a2a_research.backend.agents.pocketflow.adversary.prompt import (
    INVERSION_QUERY_PROMPT,
)
from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.models import (
    AgentRole,
    Claim,
    ClaimVerification,
)
from a2a_research.backend.core.progress import emit_llm_response, emit_prompt
from a2a_research.backend.core.settings import settings
from a2a_research.backend.core.utils.json_utils import parse_json_safely
from a2a_research.backend.core.utils.timing import perf_counter
from a2a_research.backend.llm.providers import ProviderRequestError, get_llm

logger = get_logger(__name__)


def _fallback_inversion_queries(claim_text: str) -> list[str]:
    return [
        f"{claim_text} debunked",
        f"{claim_text} controversy",
        f"{claim_text} criticism",
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


class GenerateInversionQueriesNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> dict[str, Any]:
        claim = shared.get("claim")
        if not isinstance(claim, Claim):
            raise ValueError("Adversary shared store missing Claim.")
        return {
            "claim": claim,
            "tentative_verdict": shared.get("tentative_verdict"),
        }

    async def exec_async(self, prep_res: dict[str, Any]) -> dict[str, Any]:
        claim: Claim = prep_res["claim"]
        verdict = prep_res.get("tentative_verdict")
        verdict_str = (
            verdict.verdict.value
            if isinstance(verdict, ClaimVerification)
            else "UNKNOWN"
        )

        prompt = (
            f"Claim: {claim.text}\n"
            f"Tentative verdict: {verdict_str}\n"
            f"Confidence: {getattr(verdict, 'confidence', 0.0)}"
        )

        emit_prompt(
            AgentRole.ADVERSARY,
            "inversion_queries",
            prompt,
            system_text=INVERSION_QUERY_PROMPT,
            model=settings.llm.model,
        )
        started = perf_counter()
        try:
            model = get_llm()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": INVERSION_QUERY_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning(
                "Adversary LLM failed in inversion queries: %s", exc
            )
            return {"inversion_queries": [], "error": str(exc)}

        emit_llm_response(
            AgentRole.ADVERSARY,
            "inversion_queries",
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )

        data = parse_json_safely(raw)
        queries = []
        if isinstance(data, dict):
            raw_queries = data.get("inversion_queries") or []
            if isinstance(raw_queries, list):
                queries = [
                    str(q).strip()
                    for q in raw_queries
                    if isinstance(q, str) and str(q).strip()
                ]

        if not queries:
            queries = _fallback_inversion_queries(claim.text)

        return {"inversion_queries": queries, "error": None}

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: dict[str, Any],
        exec_res: dict[str, Any],
    ) -> str:
        shared["inversion_queries"] = exec_res["inversion_queries"]
        shared["error"] = exec_res.get("error")
        return "default"


__all__ = ["GenerateInversionQueriesNode", "TerminalNode"]
