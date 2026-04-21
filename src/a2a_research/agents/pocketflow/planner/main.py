"""A2A AgentExecutor for the Planner role.

Consumes ``{query}`` (string or data part) and returns a Task with a data
artifact of ``{claims, seed_queries}`` — the handoff shape the FactChecker
expects.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

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
from a2a_research.a2a.proto import make_data_part, new_agent_text_message
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.pocketflow.planner.card import PLANNER_CARD
from a2a_research.agents.pocketflow.planner.extract import (
    extract_payload,
    extract_query,
)
from a2a_research.agents.pocketflow.planner.flow import plan
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit, using_session

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["PlannerExecutor", "build_http_app"]


class PlannerExecutor(AgentExecutor):
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        query = extract_query(context)
        payload = extract_payload(context)
        session_id = str(payload.get("session_id") or "")
        handoff_from = payload.get("handoff_from")
        if session_id and handoff_from:
            from a2a_research.progress import emit_handoff

            preview = json.dumps(
                payload, default=str, indent=2, sort_keys=True
            )
            emit_handoff(
                direction="received",
                role=AgentRole.PLANNER,
                peer_role=str(handoff_from),
                payload_keys=sorted(payload.keys()),
                payload_bytes=len(preview.encode("utf-8")),
                payload_preview=preview,
                session_id=session_id,
            )
        from a2a_research.workflow.definitions import (
            STEP_INDEX_V2 as SI,
            TOTAL_STEPS_V2 as TS,
        )
        planner_step = SI[AgentRole.PLANNER]
        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.PLANNER,
            planner_step,
            TS,
            "planner_started",
        )
        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.PLANNER,
            planner_step,
            TS,
            "decompose",
        )

        try:
            with using_session(session_id):
                plan_result = await plan(
                    query,
                    session_id=session_id,
                    include_dag=True,
                )
                claims = plan_result[0]
                claim_dag = plan_result[1] if len(plan_result) > 2 else None
                seed_queries = plan_result[-1]
            status = TaskState.TASK_STATE_COMPLETED
            error_text: str | None = None
        except Exception as exc:
            logger.exception("Planner failed task_id=%s", task.id)
            claims, claim_dag, seed_queries = [], None, []
            status = TaskState.TASK_STATE_FAILED
            error_text = str(exc)

        artifact = Artifact(
            artifact_id="plan",
            name="plan",
            parts=[
                make_data_part(
                    {
                        "query": query,
                        "claims": [c.model_dump(mode="json") for c in claims],
                        "claim_dag": (
                            claim_dag.model_dump(mode="json")
                            if claim_dag
                            else {}
                        ),
                        "seed_queries": seed_queries,
                    }
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
                    message=(
                        new_agent_text_message(error_text)
                        if error_text
                        else None
                    ),
                ),
            )
        )
        emit(
            session_id,
            (
                ProgressPhase.STEP_COMPLETED
                if status == TaskState.TASK_STATE_COMPLETED
                else ProgressPhase.STEP_FAILED
            ),
            AgentRole.PLANNER,
            planner_step,
            TS,
            (
                "planner_completed"
                if status == TaskState.TASK_STATE_COMPLETED
                else "planner_failed"
            ),
            detail=f"claims={len(claims)} seeds={len(seed_queries)}",
        )
        logger.info(
            "Planner task_id=%s claims=%s seeds=%s",
            task.id,
            len(claims),
            len(seed_queries),
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=PlannerExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=PLANNER_CARD,
    )
    return build_starlette_http_app(
        agent_card=PLANNER_CARD, http_handler=handler
    )
