"""In-process A2A client.

Builds a :class:`Message` (text + optional data payload), delegates to the
appropriate :class:`DefaultRequestHandler`'s ``on_message_send``, and returns
either the final :class:`Task` (with artifacts) or a direct response
:class:`Message`. The wire protocol is never touched — this keeps everything
in one Python process.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from a2a.types import (
    DataPart,
    Message,
    MessageSendParams,
    Part,
    Role,
    Task,
    TextPart,
)

from a2a_research.a2a.registry import AgentRegistry, get_registry
from a2a_research.app_logging import get_logger

if TYPE_CHECKING:
    from a2a_research.models import AgentRole

logger = get_logger(__name__)

__all__ = ["A2AClient", "build_message", "extract_data_payloads", "extract_text"]


def build_message(
    text: str = "",
    data: dict[str, Any] | None = None,
    *,
    role: Role = Role.user,
    task_id: str | None = None,
    context_id: str | None = None,
) -> Message:
    """Construct a :class:`Message` with an optional text part and data part."""
    parts: list[Part] = []
    if text:
        parts.append(Part(root=TextPart(text=text)))
    if data is not None:
        parts.append(Part(root=DataPart(data=data)))
    if not parts:
        parts.append(Part(root=TextPart(text="")))
    return Message(
        message_id=str(uuid.uuid4()),
        role=role,
        parts=parts,
        task_id=task_id,
        context_id=context_id,
    )


def extract_data_payloads(task_or_message: Task | Message) -> list[dict[str, Any]]:
    """Pull :class:`DataPart` payloads out of a Task's artifacts or a Message's parts."""
    payloads: list[dict[str, Any]] = []
    if isinstance(task_or_message, Task):
        for artifact in task_or_message.artifacts or []:
            for part in artifact.parts:
                root = getattr(part, "root", part)
                if isinstance(root, DataPart):
                    payloads.append(dict(root.data))
    else:
        for part in task_or_message.parts:
            root = getattr(part, "root", part)
            if isinstance(root, DataPart):
                payloads.append(dict(root.data))
    return payloads


def extract_text(task_or_message: Task | Message) -> str:
    """Concatenate :class:`TextPart` contents into a single string."""
    chunks: list[str] = []
    if isinstance(task_or_message, Task):
        for artifact in task_or_message.artifacts or []:
            for part in artifact.parts:
                root = getattr(part, "root", part)
                if isinstance(root, TextPart):
                    chunks.append(root.text)
    else:
        for part in task_or_message.parts:
            root = getattr(part, "root", part)
            if isinstance(root, TextPart):
                chunks.append(root.text)
    return "\n".join(c for c in chunks if c)


class A2AClient:
    """Thin async client that dispatches A2A messages to in-process handlers."""

    def __init__(self, registry: AgentRegistry | None = None) -> None:
        self._registry = registry or get_registry()

    async def send(
        self,
        role: AgentRole,
        payload: dict[str, Any] | None = None,
        *,
        text: str = "",
        task_id: str | None = None,
        context_id: str | None = None,
    ) -> Task | Message:
        """Send a message to ``role`` and await the final Task or Message response."""
        handler = self._registry.get_handler(role)
        message = build_message(text=text, data=payload, task_id=task_id, context_id=context_id)
        params = MessageSendParams(message=message)
        logger.info(
            "A2A.send role=%s task_id=%s payload_keys=%s",
            role.value,
            task_id,
            sorted(payload or {}),
        )
        return await handler.on_message_send(params)
