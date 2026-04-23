"""Pydantic domain models shared across agents, workflow, and UI.

Single source of truth for:

- agents/     (per-agent I/O and session mutation)
- workflow/   (top-level orchestrator state)
- a2a/        (A2A client payloads, cards, and task helpers)
- ui/         (UI-facing state and serialized payloads)
"""

from __future__ import annotations

from a2a_research.backend.core.models.claims import (
    Claim,
    ClaimDAG,
    ClaimDependency,
    ClaimFollowUp,
    FreshnessWindow,
    ReplanReason,
)
from a2a_research.backend.core.models.enums import (
    AgentCapability,
    AgentRole,
    AgentStatus,
    ProvenanceEdgeType,
    ReplanReasonCode,
    TaskStatus,
    Verdict,
)
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.core.models.evidence import (
    CredibilitySignals,
    EvidenceUnit,
    IndependenceGraph,
    Passage,
)
from a2a_research.backend.core.models.fact_checker import FactCheckerOutput
from a2a_research.backend.core.models.provenance import (
    ProvenanceEdge,
    ProvenanceNode,
    ProvenanceTree,
)
from a2a_research.backend.core.models.reports import (
    Citation,
    ReportOutput,
    ReportSection,
    WebSource,
)
from a2a_research.backend.core.models.session import (
    AgentResult,
    ResearchSession,
    workflow_roles,
)
from a2a_research.backend.core.models.verification import (
    ClaimState,
    ClaimVerification,
    VerificationRevision,
)
from a2a_research.backend.core.models.workflow import (
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
    # Workflow
    "AgentDefinition",
    # Session / Agents
    "AgentResult",
    "AgentRole",
    "AgentStatus",
    "BudgetConsumption",
    "CircuitBreakerConfig",
    # Reports
    "Citation",
    # Claims
    "Claim",
    "ClaimDAG",
    "ClaimDependency",
    "ClaimFollowUp",
    "ClaimState",
    "ClaimVerification",
    # Evidence
    "CredibilitySignals",
    # Errors
    "ErrorCode",
    "ErrorEnvelope",
    "ErrorSeverity",
    "EvidenceUnit",
    # FactChecker
    "FactCheckerOutput",
    "FreshnessWindow",
    "IndependenceGraph",
    "NoveltyTracker",
    "Passage",
    # Provenance
    "ProvenanceEdge",
    "ProvenanceEdgeType",
    "ProvenanceNode",
    "ProvenanceTree",
    "ReplanReason",
    "ReplanReasonCode",
    "ReportOutput",
    "ReportSection",
    "ResearchSession",
    "RetryPolicy",
    "TaskStatus",
    "Verdict",
    "VerificationRevision",
    "WebSource",
    "WorkflowBudget",
    "workflow_roles",
]
