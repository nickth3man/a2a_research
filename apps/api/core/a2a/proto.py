"""Helpers for working with A2A 1.0 protobuf message parts."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from a2a.types import Message, Part, Role, Task, TaskState, TaskStatus
from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.struct_pb2 import Value

__all__ = [
    "get_data_part",
    "get_text_part",
    "make_data_part",
    "make_message",
    "make_text_message",
    "make_text_part",
    "new_agent_text_message",
    "new_task",
]

ROLE_USER = Role.ROLE_USER
ROLE_AGENT = Role.ROLE_AGENT


def _serialize_for_proto(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_proto(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_proto(v) for v in obj]
    return obj


def _value_from_python(data: Any) -> Value:
    value = Value()
    ParseDict(_serialize_for_proto(data), value)
    return value


def make_text_part(text: str) -> Part:
    return Part(text=text)


def make_data_part(data: Any) -> Part:
    return Part(data=_value_from_python(data))


def get_text_part(part: Part) -> str | None:
    text = getattr(part, "text", "")
    return text or None


def get_data_part(part: Part) -> Any | None:
    if not part.HasField("data"):
        return None
    return MessageToDict(part.data, preserving_proto_field_name=True)


def make_message(
    *,
    text: str = "",
    data: Any | None = None,
    role: Role = ROLE_USER,
    task_id: str | None = None,
    context_id: str | None = None,
) -> Message:
    parts: list[Part] = []
    if text:
        parts.append(make_text_part(text))
    if data is not None:
        parts.append(make_data_part(data))
    if not parts:
        parts.append(make_text_part(""))
    return Message(
        message_id=str(uuid.uuid4()),
        role=role,
        parts=parts,
        task_id=task_id or "",
        context_id=context_id or "",
    )


def make_text_message(text: str, *, role: Role = ROLE_AGENT) -> Message:
    return make_message(text=text, role=role)


def new_agent_text_message(text: str) -> Message:
    return make_text_message(text)


def new_task(message: Message) -> Task:
    return Task(
        id=message.task_id or str(uuid.uuid4()),
        context_id=message.context_id or str(uuid.uuid4()),
        status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
    )
