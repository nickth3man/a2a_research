"""Progress-reporting helpers shared by all PocketFlow agents.

Agents receive an :class:`~a2a_research.models.A2AMessage` that optionally carries a
progress context and a :class:`~a2a_research.progress.ProgressReporter`. These helpers
decode that context and build a substep-emitting callable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from a2a_research.progress import (
    ProgressEvent,
    ProgressGranularity,
    ProgressPhase,
    ProgressReporter,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.models import A2AMessage, AgentRole


def extract_progress_context(
    message: A2AMessage | None,
) -> tuple[ProgressReporter | None, int, int, int]:
    """Return ``(reporter, step_index, total_steps, granularity)`` from ``message``."""
    if message is None:
        return None, 0, 4, 1
    reporter: ProgressReporter | None = getattr(message, "_progress_reporter", None)
    ctx: dict[str, Any] = message.payload.get("progress_context") or {}
    return (
        reporter,
        int(ctx.get("step_index", 0)),
        int(ctx.get("total_steps", 4)),
        int(ctx.get("granularity", 1)),
    )


def create_substep_emitter(
    reporter: ProgressReporter | None,
    role: AgentRole,
    step_index: int,
    total_steps: int,
    granularity: int,
    substep_total: int,
) -> Callable[..., None]:
    """Return a callable that emits a ``STEP_SUBSTEP`` event when granularity allows."""

    def emit(label: str, substep_index: int, min_granularity: int = 2, detail: str = "") -> None:
        if reporter is None or granularity < min_granularity:
            return
        reporter(
            ProgressEvent(
                phase=ProgressPhase.STEP_SUBSTEP,
                role=role,
                step_index=step_index,
                total_steps=total_steps,
                substep_label=label,
                substep_index=substep_index,
                substep_total=substep_total,
                granularity=ProgressGranularity(min(granularity, 3)),
                detail=detail,
            )
        )

    return emit
