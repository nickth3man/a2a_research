"""PocketFlow nodes for the Clarifier."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.clarifier.prompt import (
    AUDIT_PROMPT,
    DISAMBIGUATE_PROMPT,
)
from a2a_research.app_logging import get_logger
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import AgentRole
from a2a_research.progress import emit_llm_response, emit_prompt
from a2a_research.providers import ProviderRequestError, get_llm
from a2a_research.settings import settings

logger = get_logger(__name__)

__all__ = [
    "AuditNode",
    "CommitNode",
    "DisambiguateNode",
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


class DisambiguateNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> tuple[str, str]:
        query = str(shared.get("query") or "").strip()
        query_class = (
            str(shared.get("query_class") or "factual").strip().lower()
        )
        if not query:
            raise ValueError(
                "Clarifier shared store missing non-empty 'query'."
            )
        return query, query_class

    async def exec_async(self, prep_res: tuple[str, str]) -> dict[str, Any]:
        query, query_class = prep_res

        # Fast path: factual + unambiguous (heuristic: short, no slash/or/versus)
        if query_class == "factual" and _is_likely_unambiguous(query):
            return {
                "disambiguations": [],
                "committed_interpretation": query,
                "needs_disambiguation": False,
                "raw": "",
                "error": None,
            }

        user_content = f"query: {query}\nquery_class: {query_class}"
        emit_prompt(
            AgentRole.CLARIFIER,
            "disambiguate",
            user_content,
            system_text=DISAMBIGUATE_PROMPT,
            model=settings.llm.model,
        )
        started = perf_counter()
        try:
            model = get_llm()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": DISAMBIGUATE_PROMPT},
                    {"role": "user", "content": user_content},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning("Clarifier LLM disambiguation failed: %s", exc)
            return {
                "disambiguations": [],
                "committed_interpretation": query,
                "needs_disambiguation": False,
                "raw": "",
                "error": str(exc),
            }
        emit_llm_response(
            AgentRole.CLARIFIER,
            "disambiguate",
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )

        data = parse_json_safely(raw)
        disambiguations = _extract_disambiguations(data)
        committed = str(
            (data or {}).get("committed_interpretation") or query
        ).strip()
        needs = bool(
            (data or {}).get("needs_disambiguation", len(disambiguations) > 0)
        )

        # If LLM says no disambiguation needed but gave alternatives, normalize
        if not needs and disambiguations:
            needs = False
            disambiguations = []
            committed = query

        return {
            "disambiguations": disambiguations,
            "committed_interpretation": committed,
            "needs_disambiguation": needs,
            "raw": raw,
            "error": None,
        }

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: tuple[str, str],
        exec_res: dict[str, Any],
    ) -> str:
        shared["disambiguations"] = exec_res["disambiguations"]
        shared["committed_interpretation"] = exec_res[
            "committed_interpretation"
        ]
        shared["needs_disambiguation"] = exec_res["needs_disambiguation"]
        shared["raw"] = exec_res.get("raw") or ""
        shared["error"] = exec_res.get("error")
        return "default"


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
        # Pick highest confidence if committed is empty or not in list
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


class AuditNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> dict[str, Any]:
        return {
            "original_query": shared.get("query") or "",
            "query_class": shared.get("query_class") or "factual",
            "chosen_interpretation": shared.get("committed_interpretation")
            or "",
            "disambiguations": shared.get("disambiguations") or [],
        }

    async def exec_async(self, prep_res: dict[str, Any]) -> str:
        disambiguations = prep_res["disambiguations"]
        chosen = prep_res["chosen_interpretation"]
        query_class = prep_res["query_class"]

        # Fast path: no disambiguation needed
        if not disambiguations:
            if query_class == "factual":
                return "Query is factual and unambiguous; committed to original wording."
            return "No alternative interpretations required; committed to original query."

        user_content = (
            f"original_query: {prep_res['original_query']}\n"
            f"query_class: {query_class}\n"
            f"chosen_interpretation: {chosen}\n"
            f"disambiguations: {disambiguations}"
        )
        emit_prompt(
            AgentRole.CLARIFIER,
            "audit",
            user_content,
            system_text=AUDIT_PROMPT,
            model=settings.llm.model,
        )
        started = perf_counter()
        try:
            model = get_llm()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": AUDIT_PROMPT},
                    {"role": "user", "content": user_content},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning("Clarifier LLM audit failed: %s", exc)
            return f"Committed to highest-confidence interpretation: {chosen}"
        emit_llm_response(
            AgentRole.CLARIFIER,
            "audit",
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )

        data = parse_json_safely(raw)
        note = str((data or {}).get("audit_note") or "").strip()
        if note:
            return note
        return f"Committed to highest-confidence interpretation: {chosen}"

    async def post_async(
        self, shared: dict[str, Any], prep_res: dict[str, Any], exec_res: str
    ) -> str:
        shared["audit_note"] = exec_res
        return "default"


def _is_likely_unambiguous(query: str) -> bool:
    """Heuristic: short queries without comparison/opinion tokens are likely unambiguous."""
    lowered = query.lower()
    ambiguous_tokens = (
        " or ",
        " vs ",
        " versus ",
        " better ",
        " best ",
        " compare ",
        " difference ",
        " between ",
        " should i ",
        " pros and cons ",
        " opinion ",
        " think ",
        " believe ",
        " feel ",
    )
    return len(query) < 120 and not any(
        token in lowered for token in ambiguous_tokens
    )


def _extract_disambiguations(
    data: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Extract and normalize disambiguation list from LLM JSON output."""
    if not isinstance(data, dict):
        return []
    raw = data.get("disambiguations")
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            interp = str(item.get("interpretation") or "").strip()
            if interp:
                conf = float(item.get("confidence", 0.5))
                result.append(
                    {
                        "interpretation": interp,
                        "confidence": max(0.0, min(1.0, conf)),
                    }
                )
        elif isinstance(item, str) and item.strip():
            result.append({"interpretation": item.strip(), "confidence": 0.5})
    return result
