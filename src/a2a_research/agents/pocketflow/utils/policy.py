"""Concrete workflow policies built on :class:`~a2a_research.models.policy.WorkflowPolicy`.

``PipelineOrderPolicy`` is a placeholder hook for validating role transitions; the
default graph is fixed in :mod:`a2a_research.agents.pocketflow.flow`.
"""

from __future__ import annotations

from pydantic import Field

from a2a_research.models.policy import WorkflowPolicy


class PipelineOrderPolicy(WorkflowPolicy):
    required_sequence: list[str] = Field(default_factory=list)

    def validate_transition(self, from_role: str | None, to_role: str | None) -> bool:
        return True
