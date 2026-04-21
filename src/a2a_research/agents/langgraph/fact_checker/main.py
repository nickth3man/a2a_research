"""A2A AgentExecutor for the FactChecker role.

Consumes ``{query, claims, evidence, sources}`` and emits ``{verified_claims, sources}``.
Runs a single verification pass over the provided evidence.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    Artifact,
    DataPart,
    Part,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from a2a.utils import new_agent_text_message
from pydantic import ValidationError

from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.langgraph.fact_checker.card import FACT_CHECKER_CARD
from a2a_research.agents.langgraph.fact_checker.verify_route import verify_claims
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole, Claim, Verdict, WebSource
from a2a_research.progress import ProgressPhase, emit
from a2a_research.tools import PageContent

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

    from a2a_research.agents.langgraph.fact_checker.state import FactCheckRunResult

logger = get_logger(__name__)
__all__ = ["FactCheckerExecutor", "build_http_app", "run_fact_check"]


async def run_fact_check(
    query: str,
    claims: list[Claim],
    evidence: list[PageContent],
    sources: list[WebSource],
    *,
    session_id: str = "",
) -> FactCheckRunResult:
    """Verify claims against provided evidence; return ``{verified_claims, sources}``."""
    if not evidence:
        reason = "No web evidence was provided for verification."
        logger.warning("FactChecker verify short-circuit reason=%s", reason)
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
        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.FACT_CHECKER,
            3,
            5,
            "exhausted",
            detail=reason,
        )
        return {
            "verified_claims": degraded,
            "sources": sources,
            "errors": [reason],
            "search_exhausted": True,
            "rounds": 0,
        }

    verified = await verify_claims(query, claims, evidence, session_id=session_id)
    emit(
        session_id,
        ProgressPhase.STEP_SUBSTEP,
        AgentRole.FACT_CHECKER,
        3,
        5,
        "completed",
        detail=f"claims={len(verified)}",
    )
    return {
        "verified_claims": verified,
        "sources": sources,
        "errors": [],
        "search_exhausted": False,
        "rounds": 1,
    }


class FactCheckerExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        session_id = str(payload.get("session_id") or "")
        handoff_from = payload.get("handoff_from")
        if session_id and handoff_from:
            from a2a_research.progress import emit_handoff

            emit_handoff(
                direction="received",
                role=AgentRole.FACT_CHECKER,
                peer_role=str(handoff_from),
                payload_keys=sorted(payload.keys()),
                payload_bytes=len(json.dumps(payload, default=str).encode("utf-8")),
                payload_preview=json.dumps(payload, default=str, indent=2, sort_keys=True),
                session_id=session_id,
            )
        query = str(payload.get("query") or "")
        claims = _coerce_claims(payload.get("claims") or [])
        evidence = _coerce_pages(payload.get("evidence") or [])
        sources = _coerce_sources(payload.get("sources") or [])
        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.FACT_CHECKER,
            3,
            5,
            "fact_checker_started",
        )

        try:
            result: FactCheckRunResult = await run_fact_check(
                query,
                claims,
                evidence,
                sources,
                session_id=session_id,
            )
            error_text: str | None = None
            status = TaskState.completed
        except Exception as exc:
            logger.exception("FactChecker crashed task_id=%s", task.id)
            result = {
                "verified_claims": claims,
                "sources": sources,
                "errors": [f"FactChecker crashed: {exc}"],
                "search_exhausted": True,
                "rounds": 0,
            }
            status = TaskState.failed
            error_text = str(exc)

        artifact = Artifact(
            artifact_id="verified",
            name="verified",
            parts=[
                Part(
                    root=DataPart(
                        data={
                            "verified_claims": [
                                c.model_dump(mode="json") for c in result["verified_claims"]
                            ],
                            "sources": [s.model_dump(mode="json") for s in result["sources"]],
                            "errors": list(result["errors"]),
                            "search_exhausted": bool(result["search_exhausted"]),
                            "rounds": result["rounds"],
                        }
                    )
                )
            ],
        )
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task.id,
                context_id=task.context_id,
                artifact=artifact,
                append=False,
                last_chunk=True,
            )
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task.id,
                context_id=task.context_id,
                status=TaskStatus(
                    state=status,
                    message=new_agent_text_message(error_text) if error_text else None,
                ),
                final=True,
            )
        )
        emit(
            session_id,
            ProgressPhase.STEP_COMPLETED
            if status == TaskState.completed
            else ProgressPhase.STEP_FAILED,
            AgentRole.FACT_CHECKER,
            3,
            5,
            "fact_checker_completed" if status == TaskState.completed else "fact_checker_failed",
            detail=f"rounds={result['rounds']} errors={len(result['errors'])}",
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def _extract_payload(context: RequestContext) -> dict[str, Any]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        root = getattr(part, "root", part)
        if isinstance(root, DataPart):
            return dict(root.data)
        if isinstance(root, TextPart):
            try:
                data = json.loads(root.text)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                return data
    return {}


def _coerce_claims(raw: Any) -> list[Claim]:
    claims: list[Claim] = []
    for item in raw or []:
        if isinstance(item, Claim):
            claims.append(item)
            continue
        if isinstance(item, dict):
            try:
                claims.append(Claim.model_validate(item))
            except ValidationError:
                continue
    return claims


def _coerce_pages(raw: Any) -> list[PageContent]:
    pages: list[PageContent] = []
    for item in raw or []:
        if isinstance(item, PageContent):
            pages.append(item)
            continue
        if isinstance(item, dict):
            try:
                pages.append(PageContent.model_validate(item))
            except ValidationError:
                continue
    return pages


def _coerce_sources(raw: Any) -> list[WebSource]:
    sources: list[WebSource] = []
    for item in raw or []:
        if isinstance(item, WebSource):
            sources.append(item)
            continue
        if isinstance(item, dict):
            try:
                sources.append(WebSource.model_validate(item))
            except ValidationError:
                continue
    return sources


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=FactCheckerExecutor(), task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(agent_card=FACT_CHECKER_CARD, http_handler=handler).build()
