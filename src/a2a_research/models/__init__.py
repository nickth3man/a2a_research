"""Pydantic domain models shared across agents, workflow, and UI.

Single source of truth for:
- agents/     (agent I/O and session mutation)
- rag/        (chunk and retrieval types)
- workflow/   (PocketFlow shared store)
- a2a/        (in-process message contracts)
- ui/         (Mesop ``@stateclass`` fields — keep nested models concrete for Mesop serialization)

"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from a2a_research.models.artifact import (
    Artifact as Artifact,
)
from a2a_research.models.artifact import (
    ArtifactKind as ArtifactKind,
)
from a2a_research.models.artifact import (
    DataArtifact as DataArtifact,
)
from a2a_research.models.artifact import (
    StreamArtifact as StreamArtifact,
)
from a2a_research.models.artifact import (
    TextArtifact as TextArtifact,
)
from a2a_research.models.artifact import (
    wrap_in_artifact as wrap_in_artifact,
)
from a2a_research.models.envelope import A2AEnvelope as A2AEnvelope
from a2a_research.models.policy import (
    PolicyEffect as PolicyEffect,
)
from a2a_research.models.policy import (
    WorkflowPolicy as WorkflowPolicy,
)

# ─── Enums ────────────────────────────────────────────────────────────────────


class Verdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class AgentRole(StrEnum):
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    VERIFIER = "verifier"
    PRESENTER = "presenter"


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
    verdict: Verdict = Verdict.INSUFFICIENT_EVIDENCE
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


class AgentResult(BaseModel):
    role: AgentRole
    status: AgentStatus = AgentStatus.PENDING
    message: str = ""
    claims: list[Claim] = Field(default_factory=list)
    raw_content: str = ""
    citations: list[str] = Field(default_factory=list)


def default_roles() -> list[AgentRole]:
    return [
        AgentRole.RESEARCHER,
        AgentRole.ANALYST,
        AgentRole.VERIFIER,
        AgentRole.PRESENTER,
    ]


class ResearchSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    roles: list[AgentRole] = Field(default_factory=default_roles)
    agent_results: dict[AgentRole, AgentResult] = Field(default_factory=dict)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    final_report: str = ""
    error: str | None = None
    source_titles: dict[str, str] = Field(default_factory=dict)

    def get_agent(self, role: AgentRole) -> AgentResult:
        return self.agent_results.get(role, AgentResult(role=role))

    def ensure_agent_results(self) -> None:
        for role in self.roles:
            self.agent_results.setdefault(role, AgentResult(role=role))


# ─── A2A Message Contract ─────────────────────────────────────────────────────


class A2AMessage(BaseModel):
    sender: AgentRole
    recipient: AgentRole
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    payload: dict[str, Any] = Field(default_factory=dict)


# ─── Agent Card (capability declaration) ─────────────────────────────────────


class AgentCard(BaseModel):
    name: str
    role: AgentRole
    description: str
    version: str = "1.0.0"
    input_schema: dict[str, str] = Field(default_factory=dict)
    output_schema: dict[str, str] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)


AGENT_CARDS: dict[AgentRole, AgentCard] = {
    AgentRole.RESEARCHER: AgentCard(
        name="Researcher",
        role=AgentRole.RESEARCHER,
        description="Retrieves and ranks relevant documents from the RAG corpus",
        skills=["retrieval", "search", "rag", "document ranking", "semantic search"],
        input_schema={"query": "str"},
        output_schema={"retrieved_chunks": "list", "ranked_sources": "list"},
    ),
    AgentRole.ANALYST: AgentCard(
        name="Analyst",
        role=AgentRole.ANALYST,
        description="Decomposes complex claims into atomic verifiable sub-claims",
        skills=["analysis", "decomposition", "claim splitting"],
        input_schema={"text": "str"},
        output_schema={"atomic_claims": "list"},
    ),
    AgentRole.VERIFIER: AgentCard(
        name="Verifier",
        role=AgentRole.VERIFIER,
        description="Assigns SUPPORTED / REFUTED / INSUFFICIENT_EVIDENCE verdicts",
        skills=["verification", "fact-checking", "evidence assessment"],
        input_schema={"claims": "list", "evidence": "list"},
        output_schema={"sub_claim_verifications": "list", "overall_verdict": "Verdict"},
    ),
    AgentRole.PRESENTER: AgentCard(
        name="Presenter",
        role=AgentRole.PRESENTER,
        description="Synthesizes findings into structured, beautifully formatted output",
        skills=["synthesis", "presentation", "formatting", "reporting"],
        input_schema={"verifications": "list", "sources": "list"},
        output_schema={"report": "StructuredReport", "formatted_output": "str"},
    ),
}


def get_agent_card(role: AgentRole) -> AgentCard:
    return AGENT_CARDS[role]


# ─── RAG Domain Objects ───────────────────────────────────────────────────────


class DocumentChunk(BaseModel):
    id: str
    content: str
    source: str
    chunk_index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    chunk: DocumentChunk
    score: float = Field(ge=0.0, le=1.0, default=0.0)


class ResearchSource(BaseModel):
    id: str
    title: str
    content: str = ""
    relevance_score: float = Field(ge=0.0, le=1.0, default=0.0)


# ─── Agent Output Schemas ─────────────────────────────────────────────────────


class ResearcherOutput(BaseModel):
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    ranked_sources: list[ResearchSource] = Field(default_factory=list)
    research_summary: str = ""


class AnalystOutput(BaseModel):
    atomic_claims: list[Claim] = Field(default_factory=list)
    decomposition_summary: str = ""


class VerifierOutput(BaseModel):
    verified_claims: list[Claim] = Field(default_factory=list)
    verification_summary: str = ""


class PresenterOutput(BaseModel):
    report: str = ""
    formatted_output: str = ""


# ─── Workflow State ────────────────────────────────────────────────────────────


class WorkflowState(BaseModel):
    session: ResearchSession
    current_agent: AgentRole | None = None
    messages: list[A2AMessage] = Field(default_factory=list)
