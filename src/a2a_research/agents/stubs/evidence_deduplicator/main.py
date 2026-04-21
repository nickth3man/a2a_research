"""EvidenceDeduplicator — normalizes and deduplicates evidence."""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    Artifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from a2a_research.a2a.compat import build_http_app as build_starlette_http_app
from a2a_research.a2a.proto import make_data_part
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.stubs.evidence_deduplicator.card import (
    EVIDENCE_DEDUPLICATOR_CARD,
)
from a2a_research.agents.stubs.evidence_deduplicator.normalize import (
    normalize_pages_to_evidence,
)
from a2a_research.agents.stubs.evidence_deduplicator.payload import (
    _extract_payload,
)
from a2a_research.logging.app_logging import get_logger
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit

logger = get_logger(__name__)

__all__ = ["EvidenceDeduplicatorExecutor", "build_http_app"]


class EvidenceDeduplicatorExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        pages = payload.get("pages", [])
        existing = payload.get("existing_evidence", [])
        session_id = str(payload.get("session_id") or "")

        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.EVIDENCE_DEDUPLICATOR,
            6,
            12,
            "deduplicator_started",
        )

        existing_ids = {e.get("id") for e in existing if isinstance(e, dict)}
        new_evidence = normalize_pages_to_evidence(pages, existing_ids)

        result = {
            "new_evidence": new_evidence,
            "dedupe_stats": {
                "input_pages": len(pages),
                "new_evidence": len(new_evidence),
            },
            "independence_graph": {
                "claim_to_publishers": {},
                "syndication_clusters": {},
                "citation_chains": {},
            },
        }

        artifact = Artifact(
            artifact_id="normalize",
            name="normalize",
            parts=[make_data_part(result)],
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
                status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
            )
        )
        emit(
            session_id,
            ProgressPhase.STEP_COMPLETED,
            AgentRole.EVIDENCE_DEDUPLICATOR,
            6,
            12,
            "deduplicator_completed",
        )

    async def cancel(self, context, event_queue):
        pass


def build_http_app():
    handler = DefaultRequestHandler(
        agent_executor=EvidenceDeduplicatorExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=EVIDENCE_DEDUPLICATOR_CARD,
    )
    return build_starlette_http_app(
        agent_card=EVIDENCE_DEDUPLICATOR_CARD, http_handler=handler
    )
