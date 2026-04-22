"""Tests for a2a_research.a2a.request_task.initial_task_or_new."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from a2a.types import Task

from a2a_research.a2a.proto import make_message, new_task
from a2a_research.a2a.request_task import initial_task_or_new


def _make_context(
    *,
    current_task: Task | None = None,
    message=None,
) -> MagicMock:
    """Build a minimal RequestContext mock."""
    ctx = MagicMock()
    ctx.current_task = current_task
    ctx.message = message
    return ctx


class TestInitialTaskOrNew:
    def test_returns_existing_task_when_present(self) -> None:
        msg = make_message(task_id="existing-task")
        existing = new_task(msg)
        ctx = _make_context(current_task=existing)
        result = initial_task_or_new(ctx)
        assert result is existing

    def test_creates_new_task_when_no_current_task(self) -> None:
        msg = make_message(task_id="from-message")
        ctx = _make_context(message=msg)
        result = initial_task_or_new(ctx)
        assert isinstance(result, Task)

    def test_new_task_uses_message_task_id(self) -> None:
        msg = make_message(task_id="msg-task-id")
        ctx = _make_context(message=msg)
        result = initial_task_or_new(ctx)
        assert result.id == "msg-task-id"

    def test_raises_value_error_when_no_task_and_no_message(self) -> None:
        ctx = _make_context(current_task=None, message=None)
        with pytest.raises(ValueError, match="RequestContext needs a message"):
            initial_task_or_new(ctx)

    def test_existing_task_takes_priority_over_message(self) -> None:
        """current_task is returned even if message is also present."""
        msg = make_message(task_id="msg-task")
        existing = new_task(make_message(task_id="existing-id"))
        ctx = _make_context(current_task=existing, message=msg)
        result = initial_task_or_new(ctx)
        assert result is existing
        assert result.id == "existing-id"
