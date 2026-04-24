"""Tests for proto message and task builders."""

from __future__ import annotations

import uuid

from a2a.types import Message, Task, TaskState

from a2a_research.backend.core.a2a.proto import (
    ROLE_AGENT,
    ROLE_USER,
    get_data_part,
    make_message,
    make_text_message,
    new_agent_text_message,
    new_task,
)


class TestMakeMessage:
    def test_returns_message(self) -> None:
        msg = make_message()
        assert isinstance(msg, Message)

    def test_message_id_is_uuid(self) -> None:
        msg = make_message()
        parsed = uuid.UUID(msg.message_id)
        assert str(parsed) == msg.message_id

    def test_default_role_is_user(self) -> None:
        msg = make_message()
        assert msg.role == ROLE_USER

    def test_text_creates_text_part(self) -> None:
        msg = make_message(text="hello world")
        texts = [p.text for p in msg.parts if p.text]
        assert "hello world" in texts

    def test_data_creates_data_part(self) -> None:
        msg = make_message(data={"k": "v"})
        data_parts = [p for p in msg.parts if p.HasField("data")]
        assert len(data_parts) == 1
        assert get_data_part(data_parts[0]) == {"k": "v"}

    def test_no_text_no_data_creates_empty_text_part(self) -> None:
        msg = make_message()
        assert len(msg.parts) == 1
        assert msg.parts[0].text == ""

    def test_task_id_empty_when_not_provided(self) -> None:
        msg = make_message()
        assert msg.task_id == ""

    def test_task_id_set(self) -> None:
        msg = make_message(task_id="task-123")
        assert msg.task_id == "task-123"

    def test_context_id_empty_when_not_provided(self) -> None:
        msg = make_message()
        assert msg.context_id == ""

    def test_context_id_set(self) -> None:
        msg = make_message(context_id="ctx-abc")
        assert msg.context_id == "ctx-abc"

    def test_custom_role(self) -> None:
        msg = make_message(role=ROLE_AGENT)
        assert msg.role == ROLE_AGENT

    def test_text_and_data_both_present(self) -> None:
        msg = make_message(text="hi", data={"x": 1})
        assert len(msg.parts) == 2
        text_parts = [p for p in msg.parts if p.text]
        data_parts = [p for p in msg.parts if p.HasField("data")]
        assert len(text_parts) == 1
        assert len(data_parts) == 1


class TestMakeTextMessage:
    def test_returns_message_with_text(self) -> None:
        msg = make_text_message("test text")
        texts = [p.text for p in msg.parts if p.text]
        assert "test text" in texts

    def test_default_role_is_agent(self) -> None:
        msg = make_text_message("hi")
        assert msg.role == ROLE_AGENT

    def test_custom_role(self) -> None:
        msg = make_text_message("hi", role=ROLE_USER)
        assert msg.role == ROLE_USER


class TestNewAgentTextMessage:
    def test_shortcut_for_make_text_message(self) -> None:
        msg = new_agent_text_message("agent says hello")
        texts = [p.text for p in msg.parts if p.text]
        assert "agent says hello" in texts
        assert msg.role == ROLE_AGENT


class TestNewTask:
    def test_returns_task(self) -> None:
        msg = make_message(task_id="t1", context_id="c1")
        task = new_task(msg)
        assert isinstance(task, Task)

    def test_uses_message_task_id(self) -> None:
        msg = make_message(task_id="my-task-id")
        task = new_task(msg)
        assert task.id == "my-task-id"

    def test_uses_message_context_id(self) -> None:
        msg = make_message(context_id="my-context")
        task = new_task(msg)
        assert task.context_id == "my-context"

    def test_generates_task_id_when_message_has_none(self) -> None:
        msg = make_message()
        task = new_task(msg)
        assert task.id != ""
        uuid.UUID(task.id)

    def test_initial_state_is_submitted(self) -> None:
        msg = make_message(task_id="t99")
        task = new_task(msg)
        assert task.status.state == TaskState.TASK_STATE_SUBMITTED
