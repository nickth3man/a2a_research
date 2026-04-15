"""Workflow policy models for agent coordination constraints."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class PolicyEffect(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class WorkflowPolicy(BaseModel):
    name: str
    effect: PolicyEffect = PolicyEffect.ALLOW
    description: str = ""
