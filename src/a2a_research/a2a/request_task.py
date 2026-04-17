"""Resolve the in-flight :class:`Task` for an A2A ``AgentExecutor.execute`` callback."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a.utils import new_task

if TYPE_CHECKING:
    from a2a.server.agent_execution import RequestContext
    from a2a.types import Task

__all__ = ["initial_task_or_new"]


def initial_task_or_new(context: RequestContext) -> Task:
    if context.current_task is not None:
        return context.current_task
    if context.message is None:
        msg = "RequestContext needs a message when current_task is missing"
        raise ValueError(msg)
    return new_task(context.message)
