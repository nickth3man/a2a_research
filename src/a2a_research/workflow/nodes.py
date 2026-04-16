"""Actor node wrappers that call registered agents through the A2A layer."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from pocketflow import AsyncNode

from ..app_logging import get_logger
from ..models import (
    A2AMessage,
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)
from ..progress import ProgressEvent, ProgressGranularity, ProgressPhase, ProgressReporter

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
        payload = self._build_payload(self.role, session)
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
            payload["__progress_reporter__"] = progress_reporter
        logger.info(
            "Agent step start session_id=%s role=%s payload_keys=%s",
            session.id,
            self.role.value,
            sorted(payload),
        )
        started_at = perf_counter()

        from ..a2a.server import A2AClient

        message = A2AMessage(
            sender=self._get_sender_for_role(self.role),
            recipient=self.role,
            payload=payload,
        )
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

        message = A2AMessage(
            sender=self._get_sender_for_role(self.role),
            recipient=self.role,
            payload=self._build_payload(self.role, session),
        )
        shared["messages"].append(message)
        shared["current_agent"] = self.role

        if self.role == AgentRole.PRESENTER:
            session.final_report = exec_res.raw_content

        return "default"

    def _get_sender_for_role(self, role: AgentRole) -> AgentRole:
        return {
            AgentRole.RESEARCHER: AgentRole.RESEARCHER,
            AgentRole.ANALYST: AgentRole.RESEARCHER,
            AgentRole.VERIFIER: AgentRole.ANALYST,
            AgentRole.PRESENTER: AgentRole.VERIFIER,
        }.get(role, role)

    def _build_payload(self, role: AgentRole, session: ResearchSession) -> dict[str, Any]:
        if role == AgentRole.RESEARCHER:
            return {"query": session.query}
        if role == AgentRole.ANALYST:
            researcher = session.get_agent(AgentRole.RESEARCHER)
            return {
                "research_summary": researcher.raw_content,
                "citations": researcher.citations,
                "retrieved_chunks": [
                    chunk.model_dump(mode="json") for chunk in session.retrieved_chunks
                ],
            }
        if role == AgentRole.VERIFIER:
            analyst = session.get_agent(AgentRole.ANALYST)
            return {
                "claims": [c.model_dump() for c in analyst.claims],
                "query": session.query,
                "retrieved_chunks": [
                    chunk.model_dump(mode="json") for chunk in session.retrieved_chunks
                ],
            }
        if role == AgentRole.PRESENTER:
            verifier = session.get_agent(AgentRole.VERIFIER)
            return {
                "verified_claims": [c.model_dump() for c in verifier.claims],
            }
        return {}


def create_actor_node(role: AgentRole, successor_role: AgentRole | None = None) -> ActorNode:
    """Factory to create an ActorNode for any registered agent role."""
    return ActorNode(role=role, successor_role=successor_role)
