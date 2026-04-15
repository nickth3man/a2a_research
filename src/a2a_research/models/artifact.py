"""Artifact type system for extensible PocketFlow + A2A agent payloads.

Every piece of data that flows between agents is wrapped in an Artifact.
This allows future workflow runtimes to inspect, transform, and route
artifacts without coupling to domain models like Claim or AgentResult.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


class ArtifactKind(str, Enum):
    """Discriminator for artifact concrete types."""

    TEXT = "text"
    DATA = "data"
    STREAM = "stream"


T = TypeVar("T", bound=BaseModel)


class Artifact(BaseModel, ABC):
    """Abstract base for all artifacts.

    Subclasses must define `kind` and `content` and may override
    `summary` for concise UI display.
    """

    id: str = Field(default_factory=lambda: f"art_{uuid.uuid4().hex[:8]}")
    kind: ArtifactKind
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def summary(self) -> str:
        """Short description used in logs and UI brevity."""
        return self.content[:80] + ("..." if len(self.content) > 80 else "")

    @abstractmethod
    def get_content(self) -> Any:
        """Typed content accessor — each subclass overrides."""
        ...


class TextArtifact(Artifact):
    """Plain text / markdown artifact."""

    kind: ArtifactKind = ArtifactKind.TEXT
    content: str = ""

    def get_content(self) -> str:
        return self.content


class DataArtifact(Artifact):
    """Structured JSON-serialisable payload artifact."""

    kind: ArtifactKind = ArtifactKind.DATA
    data: dict[str, Any] = Field(default_factory=dict)

    def get_content(self) -> dict[str, Any]:
        return self.data


class StreamArtifact(Artifact):
    """Streaming / chunked output artifact."""

    kind: ArtifactKind = ArtifactKind.STREAM
    chunks: list[str] = Field(default_factory=list)
    completed: bool = False

    def get_content(self) -> list[str]:
        return self.chunks


def wrap_in_artifact(value: Any, kind_hint: ArtifactKind | None = None) -> Artifact:
    """Coerce a plain value into the most appropriate Artifact subtype.

    Used by future workflow runtimes to normalise heterogenous payloads.
    """
    if isinstance(value, Artifact):
        return value
    if isinstance(value, str):
        return TextArtifact(content=value)
    if isinstance(value, dict):
        return DataArtifact(data=value)
    if isinstance(value, list):
        return StreamArtifact(chunks=value)
    # Fallback: serialise whatever remains as a text artifact
    return TextArtifact(content=str(value))
