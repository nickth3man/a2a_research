"""Pydantic domain models shared across agents, workflow, and UI.

Single source of truth for:

- agents/     (per-agent I/O and session mutation)
- workflow/   (top-level orchestrator state)
- a2a/        (A2A client payloads, cards, and task helpers)
- ui/         (Mesop ``@stateclass`` fields — keep nested models
               concrete for Mesop serialization)
"""

from __future__ import annotations

from a2a_research.models.claims import (
    Claim,
    ClaimDAG,
    ClaimDependency,
    ClaimFollowUp,
    FreshnessWindow,
    ReplanReason,
)
from a2a_research.models.verification import (
    ClaimState,
    ClaimVerification,
    VerificationRevision,
)
from a2a_research.models.enums import (
    AgentCapability,
    AgentRole,
    AgentStatus,
    ProvenanceEdgeType,
    ReplanReasonCode,
    TaskStatus,
    Verdict,
)
from a2a_research.models.evidence import (
    CredibilitySignals,
    EvidenceUnit,
    IndependenceGraph,
    Passage,
)
from a2a_research.models.fact_checker import FactCheckerOutput
from a2a_research.models.provenance import (
    ProvenanceEdge,
    ProvenanceNode,
    ProvenanceTree,
)
from a2a_research.models.reports import (
    Citation,
    ReportOutput,
    ReportSection,
    WebSource,
)
from a2a_research.models.session import (
    AgentResult,
    ResearchSession,
    default_roles,
    workflow_v2_roles,
)
from a2a_research.models.workflow import (
    AgentDefinition,
    BudgetConsumption,
    CircuitBreakerConfig,
    NoveltyTracker,
    RetryPolicy,
    WorkflowBudget,
)

__all__ = [
    # Enums
    "AgentCapability",
    "AgentRole",
    "AgentStatus",
    "ProvenanceEdgeType",
    "ReplanReasonCode",
    "TaskStatus",
    "Verdict",
    # Claims
    "Claim",
    "ClaimDAG",
    "ClaimDependency",
    "ClaimFollowUp",
    "ClaimState",
    "ClaimVerification",
    "FreshnessWindow",
    "ReplanReason",
    "VerificationRevision",
    # Evidence
    "CredibilitySignals",
    "EvidenceUnit",
    "IndependenceGraph",
    "Passage",
    # Provenance
    "ProvenanceEdge",
    "ProvenanceNode",
    "ProvenanceTree",
    # Reports
    "Citation",
    "ReportOutput",
    "ReportSection",
    "WebSource",
    # Session / Agents
    "AgentResult",
    "ResearchSession",
    "default_roles",
    "workflow_v2_roles",
    # Workflow
    "AgentDefinition",
    "BudgetConsumption",
    "CircuitBreakerConfig",
    "NoveltyTracker",
    "RetryPolicy",
    "WorkflowBudget",
    # FactChecker
    "FactCheckerOutput",
]
