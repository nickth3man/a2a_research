"""Audit node for the Clarifier."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.clarifier.prompt import AUDIT_PROMPT
from a2a_research.logging.app_logging import get_logger
from a2a_research.utils.json_utils import parse_json_safely
from a2a_research.models import AgentRole
from a2a_research.progress import emit_llm_response, emit_prompt
from a2a_research.llm.providers import ProviderRequestError, get_llm
from a2a_research.settings import settings

logger = get_logger(__name__)


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

        if not disambiguations:
            if query_class == "factual":
                return (
                    "Query is factual and unambiguous; committed to original"
                    " wording."
                )
            return (
                "No alternative interpretations required; committed to"
                " original query."
            )

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
