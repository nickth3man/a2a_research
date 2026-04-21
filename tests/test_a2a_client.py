"""HTTP tests for the A2AClient wrapper."""

from __future__ import annotations

from typing import Any

import pytest
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    Artifact,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from a2a_research.a2a.client import (
    A2AClient,
    build_message,
    extract_data_payloads,
)
from a2a_research.a2a.compat import build_http_app, make_agent_card, make_skill
from a2a_research.a2a.proto import get_data_part, make_data_part, new_task
from a2a_research.a2a.registry import AgentRegistry
from a2a_research.models import AgentRole


class EchoExecutor(AgentExecutor):
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = context.current_task or new_task(context.message)  # type: ignore[arg-type]
        await event_queue.enqueue_event(task)

        payloads: list[dict[str, Any]] = []
        for part in context.message.parts if context.message else []:
            payload = get_data_part(part)
            if isinstance(payload, dict):
                payloads.append(payload)

        artifact = Artifact(
            artifact_id="echo-out",
            name="echo",
            parts=[make_data_part({"echoed": payloads})],
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

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


def _echo_app() -> Any:
    card = make_agent_card(
        name="Echo",
        description="Echo test agent",
        url="http://echo.test",
        version="1.0.0",
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        streaming=True,
        skills=[
            make_skill(
                skill_id="echo",
                name="Echo",
                description="Echo test skill",
                tags=["test"],
                input_modes=["application/json"],
                output_modes=["application/json"],
            )
        ],
    )
    handler = DefaultRequestHandler(
        agent_executor=EchoExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    return build_http_app(agent_card=card, http_handler=handler)


@pytest.mark.asyncio
async def test_client_send_returns_task_with_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from a2a_research.a2a import client as client_module

    shared_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_echo_app()),
        base_url="http://echo.test",
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
    assert any(getattr(part, "text", "") == "hello" for part in msg.parts)
    assert any(part.HasField("data") for part in msg.parts)


@pytest.mark.asyncio
async def test_client_send_includes_handoff_from_when_from_role_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from a2a_research.a2a import client as client_module

    shared_client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=_echo_app()),
        base_url="http://echo.test",
    )

    def _client_factory(*args: object, **kwargs: object) -> httpx.AsyncClient:
        return shared_client

    monkeypatch.setattr(client_module.httpx, "AsyncClient", _client_factory)

    registry = AgentRegistry(searcher_url="http://echo.test")
    client = A2AClient(registry)
    result = await client.send(
        AgentRole.SEARCHER,
        payload={"hello": "world", "session_id": "s123"},
        from_role=AgentRole.PLANNER,
    )

    assert isinstance(result, Task)
    echoed = extract_data_payloads(result)[0]["echoed"][0]
    assert echoed.get("handoff_from") == "planner"
    await shared_client.aclose()
