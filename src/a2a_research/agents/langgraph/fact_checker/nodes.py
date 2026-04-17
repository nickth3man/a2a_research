"""Node callables for the FactChecker langgraph.

The loop dispatches A2A messages to the Searcher and Reader (peer agents),
accumulates evidence, then has the LLM verify each claim. The router decides
whether to iterate again or hand off to the Synthesizer.

Error handling is explicit: if the Searcher or Reader surface provider-level
errors (e.g. Tavily disabled, DDG rate-limited, all URL fetches failed) the
errors are captured in ``state["errors"]``. If the search layer is exhausted
and we have no evidence, ``verify_node`` short-circuits to
``INSUFFICIENT_EVIDENCE`` verdicts whose ``evidence_snippets`` carry the
exact reason, and the router terminates the loop — no LLM guessing.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Literal

from a2a_research.agents.langgraph.fact_checker.prompt import VERIFY_PROMPT
from a2a_research.agents.langgraph.fact_checker.state import FactCheckState  # noqa: TC001
from a2a_research.app_logging import get_logger
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import AgentRole, Claim, Verdict, WebSource
from a2a_research.providers import ProviderRequestError, get_llm
from a2a_research.tools import PageContent, WebHit

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient

logger = get_logger(__name__)

__all__ = [
    "build_ask_reader_node",
    "build_ask_searcher_node",
    "build_verify_node",
    "route",
]


def _task_failed(task: Any) -> bool:
    status = getattr(task, "status", None)
    state = getattr(status, "state", None)
    return str(state).endswith("failed") if state is not None else False


def _task_error_metadata(task: Any) -> str | None:
    status = getattr(task, "status", None)
    metadata = getattr(status, "metadata", None) if status is not None else None
    if isinstance(metadata, dict):
        value = metadata.get("error")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def build_ask_searcher_node(client: A2AClient) -> Any:
    async def ask_searcher(state: FactCheckState) -> dict[str, Any]:
        queries = list(state.get("pending_queries") or [])
        if not queries:
            # Nothing to ask; the loop will terminate via the router.
            return {
                "hits": [],
                "pending_urls": [],
                "pending_queries": [],
                "errors": [],
                "search_exhausted": True,
            }
        from a2a_research.a2a import extract_data_payloads

        task = await client.send(AgentRole.SEARCHER, payload={"queries": queries})
        payloads = extract_data_payloads(task)
        data = payloads[0] if payloads else {}
        raw_hits = data.get("hits") or []
        raw_errors = data.get("errors") or []
        providers_successful = data.get("providers_successful") or []

        hits = [WebHit.model_validate(h) for h in raw_hits]
        errors: list[str] = [f"Searcher: {e}" for e in raw_errors if isinstance(e, str)]
        # Promote a Task-level failure message if present.
        task_err = _task_error_metadata(task)
        if _task_failed(task) and task_err:
            errors.append(f"Searcher task failed: {task_err}")

        # Search is "exhausted" when no provider ran successfully for these queries
        # AND we got zero hits — distinct from "ran but found nothing."
        exhausted = not providers_successful and not hits
        pending_urls = [h.url for h in hits[:6]]

        logger.info(
            "FactChecker ask_searcher queries=%s hits=%s urls=%s errors=%s exhausted=%s",
            len(queries),
            len(hits),
            len(pending_urls),
            len(errors),
            exhausted,
        )
        return {
            "hits": hits,
            "pending_urls": pending_urls,
            "pending_queries": [],
            "errors": errors,
            "search_exhausted": exhausted,
        }

    return ask_searcher


def build_ask_reader_node(client: A2AClient) -> Any:
    async def ask_reader(state: FactCheckState) -> dict[str, Any]:
        urls = list(state.get("pending_urls") or [])
        if not urls:
            return {"evidence": [], "sources": [], "errors": [], "pending_urls": []}
        from a2a_research.a2a import extract_data_payloads

        task = await client.send(AgentRole.READER, payload={"urls": urls})
        payloads = extract_data_payloads(task)
        data = payloads[0] if payloads else {}
        raw_pages = data.get("pages") or []
        pages = [PageContent.model_validate(p) for p in raw_pages if p]

        successful_pages = [p for p in pages if not p.error and p.markdown]
        sources = [
            WebSource(
                url=p.url,
                title=p.title or p.url,
                excerpt=(p.markdown[:280] if p.markdown else ""),
            )
            for p in successful_pages
        ]

        errors: list[str] = []
        fetch_failures = [p for p in pages if p.error]
        # Only flag as an error when every attempted URL failed to extract.
        if urls and pages and not successful_pages and fetch_failures:
            reasons = "; ".join(f"{p.url}: {p.error}" for p in fetch_failures[:3] if p.error)
            errors.append(f"Reader: every requested URL failed to extract ({reasons})")
        task_err = _task_error_metadata(task)
        if _task_failed(task) and task_err:
            errors.append(f"Reader task failed: {task_err}")

        logger.info(
            "FactChecker ask_reader urls=%s pages_ok=%s failures=%s errors=%s",
            len(urls),
            len(successful_pages),
            len(fetch_failures),
            len(errors),
        )
        return {
            "evidence": successful_pages,
            "sources": sources,
            "errors": errors,
            "pending_urls": [],
        }

    return ask_reader


def build_verify_node() -> Any:
    async def verify(state: FactCheckState) -> dict[str, Any]:
        claims = list(state.get("claims") or [])
        evidence = list(state.get("evidence") or [])
        errors = list(state.get("errors") or [])
        next_round = int(state.get("round") or 0) + 1

        # Short-circuit: no evidence means no verification is possible. Mark
        # every claim INSUFFICIENT_EVIDENCE with the exact search/read failure
        # reason in evidence_snippets, and stop the loop.
        if not evidence:
            reason = (
                "Web evidence was unavailable: " + " | ".join(errors)
                if errors
                else "No web evidence was retrieved and no provider-level errors were reported."
            )
            logger.warning(
                "FactChecker verify short-circuit round=%s reason=%s", next_round, reason
            )
            degraded = [
                c.model_copy(
                    update={
                        "verdict": Verdict.INSUFFICIENT_EVIDENCE,
                        "confidence": 0.0,
                        "sources": [],
                        "evidence_snippets": [reason],
                    }
                )
                for c in claims
            ]
            return {
                "claims": degraded,
                "round": next_round,
                "pending_queries": [],
                "search_exhausted": True,
            }

        user_content = _build_verify_prompt(state.get("query", ""), claims, evidence)
        try:
            model = get_llm()
            response = model.invoke(
                [
                    {"role": "system", "content": VERIFY_PROMPT},
                    {"role": "user", "content": user_content},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning("FactChecker LLM failed: %s", exc)
            raw = ""
        new_claims, follow_ups = _parse_verifier(raw, fallback=claims)
        logger.info(
            "FactChecker verify round=%s claims=%s follow_ups=%s",
            next_round,
            len(new_claims),
            len(follow_ups),
        )
        return {
            "claims": new_claims,
            "round": next_round,
            "pending_queries": follow_ups,
        }

    return verify


def route(state: FactCheckState) -> Literal["continue", "done"]:
    max_rounds = int(state.get("max_rounds") or 3)
    current = int(state.get("round") or 0)
    # Search layer is dead → never loop further.
    if state.get("search_exhausted"):
        return "done"
    follow_ups = list(state.get("pending_queries") or [])
    if current >= max_rounds:
        return "done"
    if not follow_ups:
        return "done"
    claims = state.get("claims") or []
    if any(c.verdict == Verdict.NEEDS_MORE_EVIDENCE for c in claims):
        return "continue"
    return "done"


def _build_verify_prompt(query: str, claims: list[Claim], evidence: list[PageContent]) -> str:
    claim_block = json.dumps(
        [
            {
                "id": c.id,
                "text": c.text,
                "verdict": c.verdict.value,
                "confidence": c.confidence,
            }
            for c in claims
        ]
    )
    evidence_block = json.dumps(
        [
            {"url": p.url, "title": p.title, "excerpt": p.markdown[:1200]}
            for p in evidence
            if not p.error and p.markdown
        ][:10]
    )
    return (
        f"Query: {query}\n\n"
        f"Claims (current state): {claim_block}\n\n"
        f"Evidence so far: {evidence_block}\n\n"
        "Return the JSON now."
    )


def _parse_verifier(raw: str, *, fallback: list[Claim]) -> tuple[list[Claim], list[str]]:
    data = parse_json_safely(raw)
    if not isinstance(data, dict):
        return fallback, []
    verified: list[Claim] = []
    for i, item in enumerate(data.get("verified_claims") or []):
        if not isinstance(item, dict):
            continue
        try:
            verdict = Verdict(str(item.get("verdict") or "NEEDS_MORE_EVIDENCE"))
        except ValueError:
            verdict = Verdict.NEEDS_MORE_EVIDENCE
        verified.append(
            Claim(
                id=str(item.get("id") or f"c{i}"),
                text=str(item.get("text") or "").strip() or f"claim_{i}",
                verdict=verdict,
                confidence=_clamp_conf(item.get("confidence")),
                sources=[str(s) for s in (item.get("sources") or []) if s],
                evidence_snippets=[str(s) for s in (item.get("evidence_snippets") or []) if s],
            )
        )
    if not verified:
        verified = fallback
    follow = [
        str(q).strip()
        for q in (data.get("follow_up_queries") or [])
        if isinstance(q, str) and q.strip()
    ]
    return verified, follow


def _clamp_conf(raw: Any, default: float = 0.5) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if value > 1.0:
        value = value / 100.0
    return max(0.0, min(1.0, value))
