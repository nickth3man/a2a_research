"""Workflow policy — constraints and routing rules for agent coordination."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class PolicyEffect(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class WorkflowPolicy(BaseModel):
    name: str
    effect: PolicyEffect = PolicyEffect.ALLOW
    description: str = ""


class PipelineOrderPolicy(WorkflowPolicy):
    required_sequence: list[str] = []

    def validate_transition(self, from_role: str | None, to_role: str | None) -> bool:
        return True
