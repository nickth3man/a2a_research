"""Core claim models and DAG operations.

Models for claims, claim dependencies, and DAG operations.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from a2a_research.backend.core.models.enums import ReplanReasonCode, Verdict


class FreshnessWindow(BaseModel):
    """Per-claim recency requirement."""

    max_age_days: int | None = None
    strict: bool = False
    rationale: str = ""


class Claim(BaseModel):
    """Immutable claim as originally decomposed by Planner."""

    id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:8]}")
    text: str
    freshness: FreshnessWindow = Field(default_factory=FreshnessWindow)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Legacy fields for backward compatibility
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    verdict: Verdict = Verdict.UNRESOLVED
    sources: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id_to_string(cls, value: Any) -> str:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        elif value is not None:
            normalized = str(value).strip()
            if normalized:
                return normalized
        msg = "Claim id must be a non-empty string."
        raise ValueError(msg)


class ClaimDependency(BaseModel):
    """Edge in the claim DAG: `child` presupposes `parent`."""

    parent_id: str
    child_id: str
    relation: Literal["presupposes", "refines", "contrasts"] = "presupposes"


class ClaimDAG(BaseModel):
    """Acyclic dependency graph over claims."""

    nodes: list[str] = Field(default_factory=list)
    edges: list[ClaimDependency] = Field(default_factory=list)

    def all_nodes(self) -> list[str]:
        """Return declared nodes plus any edge-only nodes.

        Preserves first-seen order.
        """
        seen: set[str] = set()
        ordered: list[str] = []
        for node in self.nodes:
            if node not in seen:
                seen.add(node)
                ordered.append(node)
        for edge in self.edges:
            for node in (edge.parent_id, edge.child_id):
                if node and node not in seen:
                    seen.add(node)
                    ordered.append(node)
        return ordered

    def parents_of(self, claim_id: str) -> list[str]:
        """Get parent claim IDs for a given claim."""
        return [e.parent_id for e in self.edges if e.child_id == claim_id]

    def children_of(self, claim_id: str) -> list[str]:
        """Get child claim IDs for a given claim."""
        return [e.child_id for e in self.edges if e.parent_id == claim_id]

    def descendants_of(self, claim_id: str) -> list[str]:
        """All descendants (transitive closure, BFS)."""
        result: list[str] = []
        queue = [
            child for child in self.children_of(claim_id) if child != claim_id
        ]
        visited = {claim_id}
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            result.append(current)
            queue.extend(self.children_of(current))
        return result

    def topological_order(self) -> list[str]:
        """Kahn's algorithm for topological sort."""
        all_nodes = self.all_nodes()
        in_degree = dict.fromkeys(all_nodes, 0)
        for edge in self.edges:
            in_degree[edge.child_id] = in_degree.get(edge.child_id, 0) + 1
        queue = [n for n in all_nodes if in_degree.get(n, 0) == 0]
        result: list[str] = []
        while queue:
            current = queue.pop(0)
            result.append(current)
            for child in self.children_of(current):
                in_degree[child] = in_degree.get(child, 0) - 1
                if in_degree[child] == 0:
                    queue.append(child)
        return result


class ClaimFollowUp(BaseModel):
    """Per-claim follow-up query for iterative evidence gathering."""

    claim_id: str
    claim_text: str
    reason: str
    queries: list[str] = Field(default_factory=list)
    priority: Literal["high", "medium", "low"] = "medium"
    suggested_sources: list[str] = Field(default_factory=list)
    adversarial: bool = False


class ReplanReason(BaseModel):
    """Structured reason for Planner replanning."""

    code: ReplanReasonCode
    claim_id: str | None = None
    detail: str = ""
    suggested_action: Literal["split", "merge", "drop", "add", "rephrase"] = (
        "rephrase"
    )
