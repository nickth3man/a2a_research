"""Actor node wrappers that call registered agents through the A2A layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pocketflow_reference.pocketflow_source import AsyncNode

from ..models import (
    A2AMessage,
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)

if TYPE_CHECKING:
    from a2a_research.a2a.server import A2AServer


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
        return {"session": session}

    async def exec_async(self, prep_res: dict[str, Any]) -> AgentResult:
        session: ResearchSession = prep_res["session"]

        from ..a2a.server import get_a2a_handler

        handler = get_a2a_handler(self.role)
        if handler is None:
            return AgentResult(
                role=self.role,
                status=AgentStatus.FAILED,
                message=f"No handler registered for {self.role.value}",
            )

        message = A2AMessage(
            sender=self._sender_for_role(self.role),
            recipient=self.role,
            payload=self._build_payload(self.role, session),
        )
        result = handler(session, message)
        return result

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: dict[str, Any],
        exec_res: AgentResult,
    ) -> str:
        session: ResearchSession = prep_res["session"]
        session.agent_results[self.role] = exec_res

        message = A2AMessage(
            sender=self._sender_for_role(self.role),
            recipient=self.role,
            payload=self._build_payload(self.role, session),
        )
        shared["messages"].append(message)
        shared["current_agent"] = self.role

        if self.role == AgentRole.PRESENTER:
            session.final_report = exec_res.raw_content

        return "default"

    def _sender_for_role(self, role: AgentRole) -> AgentRole:
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
            }
        if role == AgentRole.VERIFIER:
            analyst = session.get_agent(AgentRole.ANALYST)
            return {
                "claims": [c.model_dump() for c in analyst.claims],
                "query": session.query,
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
