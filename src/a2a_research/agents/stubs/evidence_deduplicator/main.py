"""EvidenceDeduplicator — normalizes and deduplicates evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlparse

from a2a.server.agent_execution import AgentExecutor, RequestContext
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
from a2a_research.a2a.proto import get_data_part, get_text_part, make_data_part
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.stubs.evidence_deduplicator.card import (
    EVIDENCE_DEDUPLICATOR_CARD,
)
from a2a_research.app_logging import get_logger
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
        new_evidence = []
        for p in pages:
            if not isinstance(p, dict):
                continue
            url = p.get("url", "")
            content = p.get("markdown", "")
            ev_id = hashlib.sha256(
                f"{url}:{content[:200]}".encode()
            ).hexdigest()[:16]
            if ev_id not in existing_ids:
                hostname = urlparse(url).hostname or ""
                publisher_id = hostname.removeprefix("www.")
                new_evidence.append(
                    {
                        "id": ev_id,
                        "url": url,
                        "canonical_url": url,
                        "title": p.get("title", ""),
                        "source_type": "other",
                        "domain_authority": 0.5,
                        "publisher_id": publisher_id,
                        "syndication_cluster_id": None,
                        "published_at": None,
                        "fetched_at": "",
                        "content_hash": ev_id,
                        "main_text": content,
                        "quoted_passages": [
                            {
                                "id": f"psg_{ev_id[:8]}",
                                "evidence_id": ev_id,
                                "text": content[:500],
                                "claim_relevance_scores": {},
                                "is_quotation": False,
                            }
                        ],
                        "credibility_signals": {
                            "domain_reputation": 0.5,
                            "author_verified": False,
                            "has_citations": False,
                            "content_freshness_days": None,
                        },
                    }
                )

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


def _extract_payload(context: RequestContext) -> dict[str, Any]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            return data_part
        text_part = get_text_part(part)
        if text_part:
            try:
                data = json.loads(text_part)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                return data
    return {}


def build_http_app():
    handler = DefaultRequestHandler(
        agent_executor=EvidenceDeduplicatorExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=EVIDENCE_DEDUPLICATOR_CARD,
    )
    return build_starlette_http_app(
        agent_card=EVIDENCE_DEDUPLICATOR_CARD, http_handler=handler
    )
