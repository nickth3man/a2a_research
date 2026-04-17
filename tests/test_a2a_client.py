"""Tests for the in-process A2AClient + AgentRegistry."""

from __future__ import annotations

from typing import Any

import pytest
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    DataPart,
    Part,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_task

from a2a_research.a2a import A2AClient, AgentRegistry, build_message, extract_data_payloads
from a2a_research.models import AgentRole


class EchoExecutor(AgentExecutor):
    """Emit one Task with a DataArtifact echoing the input payload."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task or new_task(context.message)  # type: ignore[arg-type]
        await event_queue.enqueue_event(task)

        payloads = []
        for part in context.message.parts if context.message else []:
            root = getattr(part, "root", part)
            if isinstance(root, DataPart):
                payloads.append(dict(root.data))

        combined: dict[str, Any] = {"echoed": payloads}
        artifact = Artifact(
            artifact_id="echo-out",
            name="echo",
            parts=[Part(root=DataPart(data=combined))],
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


@pytest.mark.asyncio
async def test_client_send_returns_task_with_artifact() -> None:
    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, EchoExecutor)
    client = A2AClient(registry)

    result = await client.send(AgentRole.SEARCHER, payload={"hello": "world"})

    assert result.__class__.__name__ == "Task"
    payloads = extract_data_payloads(result)
    assert payloads, "expected at least one DataPart in artifacts"
    assert payloads[0] == {"echoed": [{"hello": "world"}]}


@pytest.mark.asyncio
async def test_missing_role_raises_keyerror() -> None:
    registry = AgentRegistry()
    client = A2AClient(registry)
    with pytest.raises(KeyError, match="planner"):
        await client.send(AgentRole.PLANNER, payload={})


@pytest.mark.asyncio
async def test_build_message_includes_text_and_data() -> None:
    msg = build_message(text="hello", data={"k": 1})
    kinds = [getattr(p.root, "kind", None) for p in msg.parts]
    assert "text" in kinds and "data" in kinds
