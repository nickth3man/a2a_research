"""In-process A2A contract layer used by the LangGraph orchestration path."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from a2a_research.models import (
    A2AMessage,
    AgentCard,
    AgentResult,
    AgentRole,
    AgentStatus,
    get_agent_card,
)

if TYPE_CHECKING:
    from a2a_research.models import ResearchSession


AgentHandler = Callable[["ResearchSession", A2AMessage], AgentResult]


class A2AServer:
    """Exposes one agent's capabilities as A2A task handling."""

    def __init__(
        self,
        agent_role: AgentRole,
        handler: AgentHandler | None = None,
        card: AgentCard | None = None,
    ) -> None:
        self.role = agent_role
        self.handler = handler
        self.card = card or get_agent_card(agent_role)

    def task_handler(self, message: A2AMessage, session: ResearchSession) -> AgentResult:
        if message.recipient != self.role:
            return AgentResult(
                role=self.role,
                status=AgentStatus.FAILED,
                message=(
                    f"A2A recipient mismatch: server for {self.role.value} received "
                    f"message for {message.recipient.value}"
                ),
            )
        if self.handler is None:
            return AgentResult(
                role=self.role,
                status=AgentStatus.FAILED,
                message=f"No A2A handler registered for {self.role.value}",
            )
        return self.handler(session, message)


_SERVER_REGISTRY: dict[AgentRole, A2AServer] | None = None


def _build_server_registry() -> dict[AgentRole, A2AServer]:
    from a2a_research.agents import (
        analyst_invoke,
        presenter_invoke,
        researcher_invoke,
        verifier_invoke,
    )

    handler_map: dict[AgentRole, AgentHandler] = {
        AgentRole.RESEARCHER: researcher_invoke,
        AgentRole.ANALYST: analyst_invoke,
        AgentRole.VERIFIER: verifier_invoke,
        AgentRole.PRESENTER: presenter_invoke,
    }
    return {
        role: A2AServer(role, handler, get_agent_card(role))
        for role, handler in handler_map.items()
    }


def get_server_registry() -> dict[AgentRole, A2AServer]:
    global _SERVER_REGISTRY
    if _SERVER_REGISTRY is None:
        _SERVER_REGISTRY = _build_server_registry()
    return _SERVER_REGISTRY


class A2AClient:
    """Caller's handle on a single agent's capabilities (in-process)."""

    def __init__(self, agent_role: AgentRole) -> None:
        self.role = agent_role

    def send(self, message: A2AMessage, session: ResearchSession) -> AgentResult:
        """Block until the recipient server processes the message."""

        if message.sender != self.role:
            return AgentResult(
                role=message.recipient,
                status=AgentStatus.FAILED,
                message=(
                    f"A2A sender mismatch: client for {self.role.value} cannot send "
                    f"message from {message.sender.value}"
                ),
            )

        server = get_server_registry().get(message.recipient)
        if server is None:
            return AgentResult(
                role=message.recipient,
                status=AgentStatus.FAILED,
                message=f"No A2A server registered for {message.recipient.value}",
            )
        return server.task_handler(message, session)
