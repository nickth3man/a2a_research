"""Session and agent result models.

Models for agent execution results, the overall research session, and
role list helpers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from a2a_research.models.claims import Claim, ReplanReason
from a2a_research.models.verification import ClaimState
from a2a_research.models.enums import AgentRole, AgentStatus
from a2a_research.models.evidence import EvidenceUnit, IndependenceGraph
from a2a_research.models.provenance import ProvenanceTree
from a2a_research.models.reports import ReportOutput, WebSource
from a2a_research.models.workflow import BudgetConsumption, NoveltyTracker


class AgentResult(BaseModel):
    """Result of a single agent's execution in the pipeline."""

    role: AgentRole
    status: AgentStatus = AgentStatus.PENDING
    message: str = ""
    claims: list[Claim] = Field(default_factory=list)
    raw_content: str = ""
    citations: list[str] = Field(default_factory=list)


class ResearchSession(BaseModel):
    """Full state of a research session across all pipeline stages."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    roles: list[AgentRole] = Field(default_factory=list)
    agent_results: dict[AgentRole, AgentResult] = Field(default_factory=dict)
    sources: list[WebSource] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    report: ReportOutput | None = None
    final_report: str = ""
    error: str | None = None

    # New v2.2 fields
    claim_state: ClaimState | None = None
    accumulated_evidence: list[EvidenceUnit] = Field(default_factory=list)
    independence_graph: IndependenceGraph = Field(
        default_factory=IndependenceGraph
    )
    provenance_tree: ProvenanceTree = Field(default_factory=ProvenanceTree)
    budget_consumed: BudgetConsumption = Field(
        default_factory=BudgetConsumption
    )
    novelty_tracker: NoveltyTracker = Field(default_factory=NoveltyTracker)
    replan_reasons: list[ReplanReason] = Field(default_factory=list)
    tentative_report: ReportOutput | None = None
    critique: str = ""
    formatted_outputs: dict[str, str] = Field(default_factory=dict)

    def get_agent(self, role: AgentRole) -> AgentResult:
        """Get the result for a role, defaulting to a fresh result."""
        return self.agent_results.get(role, AgentResult(role=role))

    def ensure_agent_results(self) -> None:
        """Ensure every role has an AgentResult entry."""
        roles = self.roles if self.roles else default_roles()
        for role in roles:
            self.agent_results.setdefault(role, AgentResult(role=role))


def default_roles() -> list[AgentRole]:
    """Pipeline order for v1 simple sequential flow."""
    return [
        AgentRole.PLANNER,
        AgentRole.SEARCHER,
        AgentRole.READER,
        AgentRole.FACT_CHECKER,
        AgentRole.SYNTHESIZER,
    ]


def workflow_v2_roles() -> list[AgentRole]:
    """Full pipeline order for v2.2 claim-centric workflow."""
    return [
        AgentRole.PREPROCESSOR,
        AgentRole.CLARIFIER,
        AgentRole.PLANNER,
        AgentRole.SEARCHER,
        AgentRole.RANKER,
        AgentRole.READER,
        AgentRole.EVIDENCE_DEDUPLICATOR,
        AgentRole.FACT_CHECKER,
        AgentRole.ADVERSARY,
        AgentRole.SYNTHESIZER,
        AgentRole.CRITIC,
        AgentRole.POSTPROCESSOR,
    ]
