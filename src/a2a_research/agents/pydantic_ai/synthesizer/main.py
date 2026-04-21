"""A2A AgentExecutor for the Synthesizer.

Consumes ``{query, verified_claims, sources}`` from an incoming Message's
DataPart; returns a Task with two artifacts:

- ``report`` (DataPart) — the :class:`ReportOutput` model_dump
- ``report-markdown`` (TextPart) — rendered markdown via :meth:`ReportOutput.to_markdown`
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
from a2a_research.agents.pydantic_ai.synthesizer import agent as _agent
from a2a_research.agents.pydantic_ai.synthesizer.card import SYNTHESIZER_CARD
from a2a_research.app_logging import get_logger
from a2a_research.citation_sanitize import sanitize_report_output
from a2a_research.models import AgentRole, Claim, ReportOutput, WebSource
from a2a_research.progress import ProgressPhase, emit, emit_llm_response, emit_prompt
from a2a_research.settings import settings as _app_settings

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["SynthesizerExecutor", "build_http_app", "synthesize"]


def _build_prompt(query: str, claims: list[Claim], sources: list[WebSource]) -> str:
    claim_block = (
        "\n".join(
            f"- [{c.verdict.value}] ({c.confidence:.2f}) {c.text} sources={c.sources or []}"
            for c in claims
        )
        or "(no verified claims produced)"
    )
    source_block = (
        "\n".join(f"- {s.url} — {s.title}: {s.excerpt[:200]}" for s in sources)
        or "(no sources gathered)"
    )
    return (
        f"User query: {query}\n\n"
        f"Verified claims:\n{claim_block}\n\n"
        f"Sources:\n{source_block}\n\n"
        "Write the ReportOutput now."
    )


async def synthesize(
    query: str, claims: list[Claim], sources: list[WebSource], *, session_id: str = ""
) -> ReportOutput:
    """Run the Synthesizer agent and return the :class:`ReportOutput`."""
    agent = _agent.build_agent()
    emit(
        session_id,
        ProgressPhase.STEP_SUBSTEP,
        AgentRole.SYNTHESIZER,
        4,
        5,
        "building_prompt",
        detail=f"claims={len(claims)} sources={len(sources)}",
    )
    prompt = _build_prompt(query, claims, sources)
    emit_prompt(
        AgentRole.SYNTHESIZER,
        "synthesize",
        prompt,
        model=_app_settings.llm.model,
        session_id=session_id,
    )
    emit(session_id, ProgressPhase.STEP_SUBSTEP, AgentRole.SYNTHESIZER, 4, 5, "llm_call")
    from time import perf_counter

    started = perf_counter()
    result = await agent.run(prompt)
    report = sanitize_report_output(result.output, sources, claims)
    try:
        preview = (
            result.output.model_dump_json()
            if hasattr(result.output, "model_dump_json")
            else str(result.output)
        )
    except Exception:
        preview = str(result.output)

    prompt_tokens = None
    completion_tokens = None
    finish_reason = ""
    usage_getter = getattr(result, "usage", None)
    if callable(usage_getter):
        usage = usage_getter()
        if usage:
            prompt_tokens = getattr(usage, "request_tokens", None) or getattr(
                usage, "prompt_tokens", None
            )
            completion_tokens = getattr(usage, "response_tokens", None) or getattr(
                usage, "completion_tokens", None
            )

    emit_llm_response(
        AgentRole.SYNTHESIZER,
        "synthesize",
        preview,
        elapsed_ms=(perf_counter() - started) * 1000,
        model=_app_settings.llm.model,
        session_id=session_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        finish_reason=finish_reason,
    )
    return report


class SynthesizerExecutor(AgentExecutor):
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
                role=AgentRole.SYNTHESIZER,
                peer_role=str(handoff_from),
                payload_keys=sorted(payload.keys()),
                payload_bytes=len(json.dumps(payload, default=str).encode("utf-8")),
                payload_preview=json.dumps(payload, default=str, indent=2, sort_keys=True),
                session_id=session_id,
            )
        query = str(payload.get("query") or "")
        claims = _coerce_claims(payload.get("verified_claims") or payload.get("claims") or [])
        sources = _coerce_sources(payload.get("sources") or [])
        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.SYNTHESIZER,
            4,
            5,
            "synthesizer_started",
        )

        try:
            report = await synthesize(query, claims, sources, session_id=session_id)
            status = TaskState.completed
            error_text: str | None = None
        except Exception as exc:
            logger.exception("Synthesizer failed task_id=%s", task.id)
            report = ReportOutput(
                title="Report unavailable",
                summary=f"The Synthesizer failed: {exc}",
            )
            status = TaskState.failed
            error_text = str(exc)

        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.SYNTHESIZER,
            4,
            5,
            "rendering_markdown",
        )
        markdown = report.to_markdown()
        data_artifact = Artifact(
            artifact_id="report",
            name="report",
            parts=[Part(root=DataPart(data={"report": report.model_dump(mode="json")}))],
        )
        text_artifact = Artifact(
            artifact_id="report-markdown",
            name="report-markdown",
            parts=[Part(root=TextPart(text=markdown))],
        )
        for artifact in (data_artifact, text_artifact):
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
            AgentRole.SYNTHESIZER,
            4,
            5,
            "synthesizer_completed" if status == TaskState.completed else "synthesizer_failed",
            detail=f"report_title={report.title}",
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
        agent_executor=SynthesizerExecutor(), task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(agent_card=SYNTHESIZER_CARD, http_handler=handler).build()
