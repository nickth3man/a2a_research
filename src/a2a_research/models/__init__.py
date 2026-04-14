"""Pydantic domain models shared across agents and UI.

Single source of truth for all domain types used by:
- models/     (shared types)
- agents/     (agent I/O schemas)
- rag/        (chunk & retrieval types)
- graph/      (LangGraph state)
- a2a/        (in-process message contracts)
- ui/         (Mesop frontend)
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ─── Enums ────────────────────────────────────────────────────────────────────


class Verdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class AgentRole(str, Enum):
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    VERIFIER = "verifier"
    PRESENTER = "presenter"


class AgentStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(str, Enum):
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


class AgentResult(BaseModel):
    role: AgentRole
    status: AgentStatus = AgentStatus.PENDING
    message: str = ""
    claims: list[Claim] = Field(default_factory=list)
    raw_content: str = ""
    citations: list[str] = Field(default_factory=list)


class ResearchSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    agent_results: dict[AgentRole, AgentResult] = Field(default_factory=dict)
    final_report: str = ""
    error: str | None = None

    def get_agent(self, role: AgentRole) -> AgentResult:
        return self.agent_results.get(role, AgentResult(role=role))


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
