from __future__ import annotations

from unittest.mock import patch

from a2a_research.a2a.server import (
    A2AClient,
    A2AServer,
    get_a2a_handler,
    register_a2a_agent,
)
from a2a_research.models import A2AMessage, AgentResult, AgentRole, AgentStatus, ResearchSession


class TestA2AServer:
    def test_handle_task_rejects_mismatched_recipient(self) -> None:
        server = A2AServer(AgentRole.RESEARCHER)
        msg = A2AMessage(
            sender=AgentRole.RESEARCHER,
            recipient=AgentRole.ANALYST,
            payload={},
        )
        result = server.handle_task(msg, ResearchSession(query="q"))
        assert result.status == AgentStatus.FAILED
        assert "recipient mismatch" in result.message.lower()

    def test_handle_task_fails_when_handler_is_none(self) -> None:
        server = A2AServer(AgentRole.RESEARCHER, handler=None)
        msg = A2AMessage(
            sender=AgentRole.RESEARCHER,
            recipient=AgentRole.RESEARCHER,
            payload={},
        )
        result = server.handle_task(msg, ResearchSession(query="q"))
        assert result.status == AgentStatus.FAILED
        assert "no a2a handler registered" in result.message.lower()

    def test_handle_task_delegates_to_handler(self) -> None:
        def handler(_session: object, _message: object) -> AgentResult:
            return AgentResult(role=AgentRole.RESEARCHER, status=AgentStatus.COMPLETED)

        server = A2AServer(AgentRole.RESEARCHER, handler=handler)
        msg = A2AMessage(
            sender=AgentRole.RESEARCHER,
            recipient=AgentRole.RESEARCHER,
            payload={},
        )
        result = server.handle_task(msg, ResearchSession(query="q"))
        assert result.status == AgentStatus.COMPLETED


class TestA2AClient:
    def test_send_rejects_mismatched_sender(self) -> None:
        client = A2AClient(AgentRole.RESEARCHER)
        msg = A2AMessage(
            sender=AgentRole.ANALYST,
            recipient=AgentRole.VERIFIER,
            payload={},
        )
        result = client.send(msg, ResearchSession(query="q"))
        assert result.status == AgentStatus.FAILED
        assert "sender mismatch" in result.message.lower()

    def test_send_fails_when_server_unregistered(self) -> None:
        client = A2AClient(AgentRole.RESEARCHER)
        msg = A2AMessage(
            sender=AgentRole.RESEARCHER,
            recipient=AgentRole.PRESENTER,
            payload={},
        )
        with patch("a2a_research.a2a.server.get_server_registry", return_value={}):
            result = client.send(msg, ResearchSession(query="q"))
        assert result.status == AgentStatus.FAILED
        assert "no a2a server registered" in result.message.lower()


class TestRegistration:
    def test_register_a2a_agent_overrides_existing(self) -> None:
        def new_handler(_session: object, _message: object) -> AgentResult:
            return AgentResult(role=AgentRole.VERIFIER, status=AgentStatus.COMPLETED)

        register_a2a_agent(AgentRole.VERIFIER, new_handler)
        handler = get_a2a_handler(AgentRole.VERIFIER)
        assert handler is new_handler
