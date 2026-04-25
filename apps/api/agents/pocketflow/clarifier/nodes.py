"""PocketFlow nodes for the Clarifier."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncNode

from agents.pocketflow.clarifier.nodes_audit import (
    AuditNode,
)
from agents.pocketflow.clarifier.nodes_commit import (
    CommitNode,
)
from agents.pocketflow.clarifier.nodes_helpers import (
    _extract_disambiguations,
    _is_likely_unambiguous,
)
from agents.pocketflow.clarifier.nodes_terminal import (
    TerminalNode,
)
from agents.pocketflow.clarifier.prompt import (
    DISAMBIGUATE_PROMPT,
)
from core import (
    AgentRole,
    emit_llm_response,
    emit_prompt,
    get_logger,
    parse_json_safely,
    settings,
)
from llm import ProviderRequestError, get_llm

logger = get_logger(__name__)

__all__ = [
    "AuditNode",
    "CommitNode",
    "DisambiguateNode",
    "TerminalNode",
]


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
        from time import perf_counter

        query, query_class = prep_res

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
