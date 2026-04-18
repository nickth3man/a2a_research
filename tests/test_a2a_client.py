"""HTTP tests for the A2AClient wrapper."""

from __future__ import annotations

from typing import Any

import pytest
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Artifact,
    DataPart,
    Part,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_task

from a2a_research.a2a.client import A2AClient, build_message, extract_data_payloads
from a2a_research.a2a.registry import AgentRegistry
from a2a_research.models import AgentRole


class EchoExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task(context.message)  # type: ignore[arg-type]
        await event_queue.enqueue_event(task)

        payloads: list[dict[str, Any]] = []
        for part in context.message.parts if context.message else []:
            root = getattr(part, "root", part)
            if isinstance(root, DataPart):
                payloads.append(dict[str, Any](root.data))

        artifact = Artifact(
            artifact_id="echo-out",
            name="echo",
            parts=[Part(root=DataPart(data={"echoed": payloads}))],
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
                status=TaskStatus(state=TaskState.completed),
                final=True,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def _echo_app() -> Any:
    card = AgentCard(
        name="Echo",
        description="Echo test agent",
        version="1.0.0",
        protocol_version="0.3.0",
        url="http://echo.test",
        preferred_transport="JSONRPC",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[
            AgentSkill(
                id="echo",
                name="Echo",
                description="Echo test skill",
                tags=["test"],
                input_modes=["application/json"],
                output_modes=["application/json"],
            )
        ],
    )
    handler = DefaultRequestHandler(agent_executor=EchoExecutor(), task_store=InMemoryTaskStore())
    return A2AStarletteApplication(agent_card=card, http_handler=handler).build()


@pytest.mark.asyncio
async def test_client_send_returns_task_with_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from a2a_research.a2a import client as client_module

    shared_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_echo_app()), base_url="http://echo.test"
    )

    def _client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        return shared_client

    monkeypatch.setattr(client_module.httpx, "AsyncClient", _client_factory)

    registry = AgentRegistry(searcher_url="http://echo.test")
    client = A2AClient(registry)
    result = await client.send(AgentRole.SEARCHER, payload={"hello": "world"})

    assert isinstance(result, Task)
    assert extract_data_payloads(result)[0] == {"echoed": [{"hello": "world"}]}
    await shared_client.aclose()


@pytest.mark.asyncio
async def test_build_message_includes_text_and_data() -> None:
    msg = build_message(text="hello", data={"k": 1})
    kinds = [getattr(part.root, "kind", None) for part in msg.parts]
    assert "text" in kinds and "data" in kinds
