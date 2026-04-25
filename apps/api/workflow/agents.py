"""Agent execution helper for the workflow engine."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import TYPE_CHECKING, Any

from core import get_logger
from core.models import (
    AgentRole,
    AgentStatus,
    ResearchSession,
)
from workflow import payload, set_status, task_failed
from workflow.definitions import (
    AGENT_DEFINITIONS,
    stage_timeout,
)

if TYPE_CHECKING:
    from core import A2AClient

logger = get_logger(__name__)

__all__ = ["run_agent"]


async def run_agent(
    session: ResearchSession,
    client: A2AClient,
    role: AgentRole,
    agent_payload: dict[str, Any],
    *,
    agent_timeout: float | None = None,
) -> dict[str, Any]:
    """Call an agent via A2A and return its payload.

    If the agent is not registered (new agents not yet deployed),
    returns a passthrough result so the workflow can degrade gracefully.
    """
    stage_to = (
        agent_timeout if agent_timeout is not None else stage_timeout(role)
    )
    definition = AGENT_DEFINITIONS.get(role)
    if definition is None:
        return dict(agent_payload)

    set_status(session, role, AgentStatus.RUNNING, f"Calling {role.value}…")

    try:
        t0 = perf_counter()

        task = await asyncio.wait_for(
            client.send(
                role, payload=agent_payload, from_role=AgentRole.PLANNER
            ),
            timeout=stage_to,
        )
        session.budget_consumed.http_calls += 1
    except TimeoutError:
        logger.warning("Agent %s timed out after %.1fs", role.value, stage_to)
        set_status(
            session,
            role,
            AgentStatus.FAILED,
            f"Timeout after {stage_to:.0f}s.",
        )
        return {}
    except Exception as exc:
        logger.warning("Agent %s unreachable: %s", role.value, exc)
        set_status(session, role, AgentStatus.FAILED, f"Unreachable: {exc}")
        return {}

    if task_failed(task):
        set_status(
            session, role, AgentStatus.FAILED, "Agent reported failure."
        )
        return {}

    data = payload(task)
    elapsed = (perf_counter() - t0) * 1000
    set_status(
        session, role, AgentStatus.COMPLETED, "Done.", elapsed_ms=elapsed
    )
    return data
