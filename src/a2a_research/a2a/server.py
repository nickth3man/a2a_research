"""In-process A2A server stubs: :class:`A2AServer`, :class:`A2AClient`, registration helpers.

Maps each :class:`~a2a_research.models.AgentRole` to a callable that accepts
``(ResearchSession, A2AMessage)`` and returns an :class:`~a2a_research.models.AgentResult`,
wrapping the lower-level handlers from :mod:`a2a_research.agents.registry`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from a2a_research.models import A2AMessage, AgentCard, AgentResult, AgentRole, AgentStatus

if TYPE_CHECKING:
    from a2a_research.models import ResearchSession


AgentHandler = Callable[["ResearchSession", A2AMessage], AgentResult]


class A2AServer:
    def __init__(
        self,
        agent_role: AgentRole,
        handler: AgentHandler | None = None,
        card: AgentCard | None = None,
    ) -> None:
        self.role = agent_role
        self.handler = handler
        self.card = card or AgentCard(
            name=agent_role.value.title(),
            role=agent_role,
            description=f"A2A server for {agent_role.value}",
        )

    def handle_task(self, message: A2AMessage, session: ResearchSession) -> AgentResult:
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
    from a2a_research.models import get_agent_card

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


def register_a2a_agent(
    role: AgentRole,
    handler: AgentHandler,
    card: AgentCard | None = None,
) -> None:
    from a2a_research.models import get_agent_card

    registry = get_server_registry()
    registry[role] = A2AServer(role, handler, card or get_agent_card(role))


def get_a2a_handler(role: AgentRole) -> AgentHandler | None:
    server = get_server_registry().get(role)
    return server.handler if server else None


def reset_server_registry() -> None:
    global _SERVER_REGISTRY
    _SERVER_REGISTRY = None


class A2AClient:
    def __init__(self, agent_role: AgentRole) -> None:
        self.role = agent_role

    def send(self, message: A2AMessage, session: ResearchSession) -> AgentResult:
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
        return server.handle_task(message, session)
