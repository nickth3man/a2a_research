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
from a2a.utils import new_task
from pydantic import ValidationError

from a2a_research.agents.pydantic_ai.synthesizer import agent as _agent
from a2a_research.app_logging import get_logger
from a2a_research.models import Claim, ReportOutput, WebSource

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["SynthesizerExecutor", "synthesize"]


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


async def synthesize(query: str, claims: list[Claim], sources: list[WebSource]) -> ReportOutput:
    """Run the Synthesizer agent and return the :class:`ReportOutput`."""
    agent = _agent.build_agent()
    prompt = _build_prompt(query, claims, sources)
    result = await agent.run(prompt)
    return result.output


class SynthesizerExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task(context.message)  # type: ignore[arg-type]
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        query = str(payload.get("query") or "")
        claims = _coerce_claims(payload.get("verified_claims") or payload.get("claims") or [])
        sources = _coerce_sources(payload.get("sources") or [])

        try:
            report = await synthesize(query, claims, sources)
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
                status=TaskStatus(state=status, message=None),
                final=True,
                metadata={"error": error_text} if error_text else None,
            )
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
