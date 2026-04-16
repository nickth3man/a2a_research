"""Actor node wrappers that call registered agents through the A2A layer."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.utils.actor_helpers import (
    build_payload,
    get_sender_for_role,
)
from a2a_research.app_logging import get_logger
from a2a_research.models import (
    A2AMessage,
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)
from a2a_research.progress import (
    ProgressEvent,
    ProgressGranularity,
    ProgressPhase,
    ProgressReporter,
)

logger = get_logger(__name__)


class ActorNode(AsyncNode):
    """Async node that invokes a single agent via the A2A layer.

    Shared state carries a ResearchSession. prep_async extracts the
    session; exec_async calls the agent handler through A2A; post_async
    records the result and appends the A2A message.
    """

    def __init__(
        self,
        role: AgentRole,
        successor_role: AgentRole | None = None,
        max_retries: int = 1,
        wait: float = 0,
    ) -> None:
        super().__init__(max_retries=max_retries, wait=int(wait))
        self.role = role
        self.successor_role = successor_role

    async def prep_async(self, shared: dict[str, Any]) -> dict[str, Any]:
        session = shared.get("session")
        if session is None:
            raise ValueError("Shared state missing 'session'")
        return {"session": session, "shared": shared}

    async def exec_async(self, prep_res: dict[str, Any]) -> AgentResult:
        session: ResearchSession = prep_res["session"]
        shared: dict[str, Any] = prep_res["shared"]
        progress_reporter: ProgressReporter | None = shared.get("progress_reporter")
        total_steps = len(session.roles)
        step_index = session.roles.index(self.role) if self.role in session.roles else 0
        session.ensure_agent_results()
        session.agent_results[self.role] = AgentResult(
            role=self.role,
            status=AgentStatus.RUNNING,
            message=f"{self.role.value.title()} is running.",
        )
        payload = build_payload(self.role, session)
        if progress_reporter:
            progress_reporter(
                ProgressEvent(
                    phase=ProgressPhase.STEP_STARTED,
                    role=self.role,
                    step_index=step_index,
                    total_steps=total_steps,
                    substep_label=f"{self.role.value.title()} started.",
                    granularity=ProgressGranularity.AGENT,
                )
            )
            granularity = shared.get("progress_granularity", 1)
            payload["progress_context"] = {
                "step_index": step_index,
                "total_steps": total_steps,
                "granularity": granularity,
            }
        logger.info(
            "Agent step start session_id=%s role=%s payload_keys=%s",
            session.id,
            self.role.value,
            sorted(payload),
        )
        started_at = perf_counter()

        from a2a_research.a2a.server import A2AClient

        message = A2AMessage(
            sender=get_sender_for_role(self.role),
            recipient=self.role,
            payload=payload,
        )
        if progress_reporter is not None:
            # Attach reporter directly to the message instance so it does not cross
            # the A2A payload boundary (payload is serialized; this private attr is not).
            object.__setattr__(message, "_progress_reporter", progress_reporter)
        # Store the message so post_async can reuse it without rebuilding the payload.
        prep_res["message"] = message
        client = A2AClient(message.sender)
        try:
            result = await asyncio.to_thread(client.send, message, session)
        except Exception:
            elapsed_ms = (perf_counter() - started_at) * 1000
            if progress_reporter:
                progress_reporter(
                    ProgressEvent(
                        phase=ProgressPhase.STEP_FAILED,
                        role=self.role,
                        step_index=step_index,
                        total_steps=total_steps,
                        substep_label=f"{self.role.value.title()} failed.",
                        granularity=ProgressGranularity.AGENT,
                        elapsed_ms=elapsed_ms,
                    )
                )
            logger.exception(
                "Agent step failed session_id=%s role=%s elapsed_ms=%.1f",
                session.id,
                self.role.value,
                elapsed_ms,
            )
            raise
        elapsed_ms = (perf_counter() - started_at) * 1000
        if progress_reporter:
            progress_reporter(
                ProgressEvent(
                    phase=ProgressPhase.STEP_COMPLETED,
                    role=self.role,
                    step_index=step_index,
                    total_steps=total_steps,
                    substep_label=result.message or f"{self.role.value.title()} completed.",
                    granularity=ProgressGranularity.AGENT,
                    elapsed_ms=elapsed_ms,
                )
            )
        logger.info(
            "Agent step completed session_id=%s role=%s status=%s elapsed_ms=%.1f message=%r",
            session.id,
            self.role.value,
            result.status.value,
            elapsed_ms,
            result.message,
        )
        return result

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: dict[str, Any],
        exec_res: AgentResult,
    ) -> str:
        session: ResearchSession = prep_res["session"]
        session.agent_results[self.role] = exec_res
        session.error = exec_res.message if exec_res.status == AgentStatus.FAILED else None

        message: A2AMessage = prep_res.get("message") or A2AMessage(
            sender=get_sender_for_role(self.role),
            recipient=self.role,
            payload=build_payload(self.role, session),
        )
        shared["messages"].append(message)
        shared["current_agent"] = self.role

        if self.role == AgentRole.PRESENTER:
            session.final_report = exec_res.raw_content

        return "default"


def create_actor_node(role: AgentRole, successor_role: AgentRole | None = None) -> ActorNode:
    """Factory to create an ActorNode for any registered agent role."""
    return ActorNode(role=role, successor_role=successor_role)
