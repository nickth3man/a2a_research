"""Pydantic domain models shared across agents, workflow, and UI.

Single source of truth for:

- agents/     (per-agent I/O and session mutation)
- workflow/   (top-level orchestrator state)
- a2a/        (A2A client payloads, cards, and task helpers)
- ui/         (Mesop ``@stateclass`` fields — keep nested models concrete for Mesop serialization)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "AgentResult",
    "AgentRole",
    "AgentStatus",
    "Citation",
    "Claim",
    "ReportOutput",
    "ReportSection",
    "ResearchSession",
    "TaskStatus",
    "Verdict",
    "WebSource",
    "default_roles",
]

# ─── Enums ────────────────────────────────────────────────────────────────────


class Verdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"


class AgentRole(StrEnum):
    PLANNER = "planner"
    SEARCHER = "searcher"
    READER = "reader"
    FACT_CHECKER = "fact_checker"
    SYNTHESIZER = "synthesizer"


class AgentStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(StrEnum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Core Domain Objects ──────────────────────────────────────────────────────


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:8]}")
    text: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    verdict: Verdict = Verdict.NEEDS_MORE_EVIDENCE
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


class WebSource(BaseModel):
    """A web resource discovered during research (URL-level citation)."""

    url: str
    title: str = ""
    excerpt: str = ""
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Citation(BaseModel):
    """Inline citation attached to a report section."""

    url: str
    title: str = ""
    quote: str = ""


class ReportSection(BaseModel):
    heading: str
    body: str
    citations: list[Citation] = Field(default_factory=list)


class ReportOutput(BaseModel):
    """Structured final report produced by the Synthesizer."""

    title: str
    summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Render the report as markdown (used by UI report panel)."""
        parts: list[str] = [f"# {self.title}", "", self.summary.strip(), ""]
        for section in self.sections:
            parts.append(f"## {section.heading}")
            parts.append("")
            parts.append(section.body.strip())
            parts.append("")
        if self.citations:
            parts.append("## Sources")
            parts.append("")
            for i, c in enumerate(self.citations, 1):
                label = c.title or c.url
                parts.append(f"{i}. [{label}]({c.url})")
        return "\n".join(parts).strip() + "\n"


class AgentResult(BaseModel):
    role: AgentRole
    status: AgentStatus = AgentStatus.PENDING
    message: str = ""
    claims: list[Claim] = Field(default_factory=list)
    raw_content: str = ""
    citations: list[str] = Field(default_factory=list)


def default_roles() -> list[AgentRole]:
    """Pipeline order: Planner → Searcher → Reader → FactChecker → Synthesizer."""
    return [
        AgentRole.PLANNER,
        AgentRole.SEARCHER,
        AgentRole.READER,
        AgentRole.FACT_CHECKER,
        AgentRole.SYNTHESIZER,
    ]


class ResearchSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    roles: list[AgentRole] = Field(default_factory=default_roles)
    agent_results: dict[AgentRole, AgentResult] = Field(default_factory=dict)
    sources: list[WebSource] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    report: ReportOutput | None = None
    final_report: str = ""
    error: str | None = None

    def get_agent(self, role: AgentRole) -> AgentResult:
        return self.agent_results.get(role, AgentResult(role=role))

    def ensure_agent_results(self) -> None:
        for role in self.roles:
            self.agent_results.setdefault(role, AgentResult(role=role))
