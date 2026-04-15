"""A2A envelope — lightweight wrapper for agent-to-agent messages."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from a2a_research.models import A2AMessage


class A2AEnvelope(BaseModel):
    message: A2AMessage
    trace_id: str | None = None
    route_policy: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
