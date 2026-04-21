"""Pydantic domain models shared across agents, workflow, and UI.

Single source of truth for:

- agents/     (per-agent I/O and session mutation)
- workflow/   (top-level orchestrator state)
- a2a/        (A2A client payloads, cards, and task helpers)
- ui/         (Mesop ``@stateclass`` fields — keep nested models concrete for Mesop serialization)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

__all__ = [
    # Enums
    "AgentCapability",
    "AgentDefinition",
    # Legacy / UI
    "AgentResult",
    "AgentRole",
    "AgentStatus",
    # Workflow
    "BudgetConsumption",
    "CircuitBreakerConfig",
    "Citation",
    "Claim",
    "ClaimDAG",
    "ClaimDependency",
    "ClaimFollowUp",
    "ClaimState",
    "ClaimVerification",
    "CredibilitySignals",
    "EvidenceUnit",
    # Core domain
    "FreshnessWindow",
    "IndependenceGraph",
    "NoveltyTracker",
    # Evidence
    "Passage",
    "ProvenanceEdge",
    "ProvenanceEdgeType",
    # Provenance
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
    "default_roles",
    "workflow_v2_roles",
]

# ─── Enums ────────────────────────────────────────────────────────────────────


class Verdict(StrEnum):
    """Claim verification verdicts."""

    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"
    MIXED = "MIXED"
    UNRESOLVED = "UNRESOLVED"
    STALE = "STALE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"


class AgentRole(StrEnum):
    """Named pipeline participants."""

    PREPROCESSOR = "preprocessor"
    CLARIFIER = "clarifier"
    PLANNER = "planner"
    SEARCHER = "searcher"
    RANKER = "ranker"
    READER = "reader"
    EVIDENCE_DEDUPLICATOR = "evidence_deduplicator"
    FACT_CHECKER = "fact_checker"
    ADVERSARY = "adversary"
    SYNTHESIZER = "synthesizer"
    CRITIC = "critic"
    POSTPROCESSOR = "postprocessor"


class AgentCapability(StrEnum):
    """What an agent can do."""

    PREPROCESS = "preprocess"
    CLARIFY = "clarify"
    DECOMPOSE = "decompose"
    REPLAN = "replan"
    SEARCH = "search"
    RANK = "rank"
    EXTRACT = "extract"
    NORMALIZE = "normalize"
    VERIFY = "verify"
    ADVERSARIAL_VERIFY = "adversarial_verify"
    FOLLOW_UP = "follow_up"
    SYNTHESIZE = "synthesize"
    CRITIQUE = "critique"
    POSTPROCESS = "postprocess"


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


class ReplanReasonCode(StrEnum):
    TOO_BROAD = "too_broad"
    TOO_NARROW = "too_narrow"
    MISSING_CLAIM = "missing_claim"
    REDUNDANT_CLAIM = "redundant_claim"
    WRONG_DOMAIN = "wrong_domain"
    AMBIGUOUS_TERM = "ambiguous_term"


class ProvenanceEdgeType(StrEnum):
    CLAIM_TO_QUERY = "claim_to_query"
    QUERY_TO_HIT = "query_to_hit"
    HIT_TO_PAGE = "hit_to_page"
    PAGE_TO_PASSAGE = "page_to_passage"
    PASSAGE_TO_VERDICT = "passage_to_verdict"
    PASSAGE_TO_ADVERSARY_CHALLENGE = "passage_to_adversary_challenge"


# ─── Core Claim Models ────────────────────────────────────────────────────────


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
        """Return declared nodes plus any edge-only nodes, preserving first-seen order."""
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
        return [e.parent_id for e in self.edges if e.child_id == claim_id]

    def children_of(self, claim_id: str) -> list[str]:
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


class VerificationRevision(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    previous_verdict: Literal[
        "SUPPORTED", "REFUTED", "MIXED", "UNRESOLVED", "STALE"
    ]
    new_verdict: Literal[
        "SUPPORTED", "REFUTED", "MIXED", "UNRESOLVED", "STALE"
    ]
    reason: str
    evidence_delta: list[str] = Field(default_factory=list)


class ClaimVerification(BaseModel):
    """Mutable verification state for a claim."""

    claim_id: str
    verdict: Verdict = Verdict.UNRESOLVED
    confidence: float = 0.0
    independent_source_count: int = 0
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    refuting_evidence_ids: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    adversary_result: Literal["HOLDS", "WEAKENED", "REFUTED", "NOT_RUN"] = (
        "NOT_RUN"
    )
    revision_history: list[VerificationRevision] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ClaimState(BaseModel):
    """Aggregated verification state for all claims."""

    original_claims: list[Claim] = Field(default_factory=list)
    dag: ClaimDAG = Field(default_factory=ClaimDAG)
    verification: dict[str, ClaimVerification] = Field(default_factory=dict)
    unresolved_claim_ids: list[str] = Field(default_factory=list)
    stale_claim_ids: list[str] = Field(default_factory=list)
    resolved_claim_ids: list[str] = Field(default_factory=list)

    def mark_dependents_stale(self, parent_id: str) -> None:
        """Cascade STALE to descendants when a parent verdict flips."""
        for descendant in self.dag.descendants_of(parent_id):
            v = self.verification.get(descendant)
            if v is not None:
                v.verdict = Verdict.STALE
                if descendant in self.unresolved_claim_ids:
                    self.unresolved_claim_ids.remove(descendant)
                if descendant not in self.stale_claim_ids:
                    self.stale_claim_ids.append(descendant)
                if descendant in self.resolved_claim_ids:
                    self.resolved_claim_ids.remove(descendant)

    def refresh_resolution_lists(self) -> None:
        """Derive unresolved / stale / resolved ids from current verification verdicts."""
        unresolved: list[str] = []
        stale: list[str] = []
        resolved: list[str] = []
        ordered_claim_ids = [claim.id for claim in self.original_claims]
        for claim_id in self.verification:
            if claim_id not in ordered_claim_ids:
                ordered_claim_ids.append(claim_id)
        for claim_id in ordered_claim_ids:
            verification = self.verification.get(claim_id)
            verdict = (
                verification.verdict
                if verification is not None
                else Verdict.UNRESOLVED
            )
            if verdict == Verdict.STALE:
                stale.append(claim_id)
            elif verdict == Verdict.UNRESOLVED:
                unresolved.append(claim_id)
            else:
                resolved.append(claim_id)
        self.unresolved_claim_ids = unresolved
        self.stale_claim_ids = stale
        self.resolved_claim_ids = resolved

    def get_claim(self, claim_id: str) -> Claim | None:
        for claim in self.original_claims:
            if claim.id == claim_id:
                return claim
        return None

    @property
    def all_resolved(self) -> bool:
        return not self.unresolved_claim_ids and not self.stale_claim_ids

    @property
    def tentatively_supported_claim_ids(self) -> list[str]:
        return [
            cid
            for cid, v in self.verification.items()
            if v.verdict == Verdict.SUPPORTED
            and v.adversary_result == "NOT_RUN"
        ]

    @property
    def unresolved_or_stale_claims(self) -> list[Claim]:
        ids = set(self.unresolved_claim_ids + self.stale_claim_ids)
        return [c for c in self.original_claims if c.id in ids]

    @property
    def unresolved_or_stale_claim_ids(self) -> list[str]:
        return list(set(self.unresolved_claim_ids + self.stale_claim_ids))

    @property
    def freshness_windows(self) -> dict[str, FreshnessWindow]:
        return {c.id: c.freshness for c in self.original_claims}


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


# ─── Evidence Models ──────────────────────────────────────────────────────────


class Passage(BaseModel):
    """A passage extracted from evidence."""

    id: str = Field(default_factory=lambda: f"psg_{uuid.uuid4().hex[:8]}")
    evidence_id: str
    text: str
    claim_relevance_scores: dict[str, float] = Field(default_factory=dict)
    is_quotation: bool = False


class CredibilitySignals(BaseModel):
    """Signals about evidence credibility."""

    domain_reputation: float = 0.0
    author_verified: bool = False
    has_citations: bool = False
    content_freshness_days: int | None = None


class EvidenceUnit(BaseModel):
    """Normalized evidence with stable IDs and source independence tracking."""

    id: str = Field(default_factory=lambda: f"evu_{uuid.uuid4().hex[:8]}")
    url: str
    canonical_url: str = ""
    title: str = ""
    source_type: Literal[
        "academic", "news", "blog", "wiki", "forum", "social", "other"
    ] = "other"
    domain_authority: float = 0.0
    publisher_id: str = ""
    syndication_cluster_id: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = ""
    main_text: str = ""
    quoted_passages: list[Passage] = Field(default_factory=list)
    credibility_signals: CredibilitySignals = Field(
        default_factory=CredibilitySignals
    )


class IndependenceGraph(BaseModel):
    """Tracks independent vs syndicated sources per claim."""

    claim_to_publishers: dict[str, set[str]] = Field(default_factory=dict)
    syndication_clusters: dict[str, list[str]] = Field(default_factory=dict)
    citation_chains: dict[str, list[str]] = Field(default_factory=dict)

    def independent_source_count(self, claim_id: str) -> int:
        """Distinct publishers after collapsing syndication clusters."""
        publishers = self.claim_to_publishers.get(claim_id, set())
        return len(publishers)

    def update(self, evidence_units: list[EvidenceUnit]) -> None:
        """Ingest new evidence and update publisher mappings."""
        for ev in evidence_units:
            if ev.syndication_cluster_id:
                members = self.syndication_clusters.setdefault(
                    ev.syndication_cluster_id, []
                )
                if ev.id not in members:
                    members.append(ev.id)
            for passage in ev.quoted_passages:
                for claim_id in passage.claim_relevance_scores:
                    if claim_id not in self.claim_to_publishers:
                        self.claim_to_publishers[claim_id] = set()
                    if ev.publisher_id:
                        self.claim_to_publishers[claim_id].add(ev.publisher_id)


# ─── Provenance Models ────────────────────────────────────────────────────────


class ProvenanceNode(BaseModel):
    """Node in the provenance tree."""

    id: str = Field(default_factory=lambda: f"prv_{uuid.uuid4().hex[:8]}")
    node_type: Literal[
        "claim", "query", "hit", "page", "passage", "verdict", "challenge"
    ] = "claim"
    ref_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProvenanceEdge(BaseModel):
    """Edge in the provenance tree."""

    src: str
    dst: str
    edge_type: ProvenanceEdgeType = ProvenanceEdgeType.CLAIM_TO_QUERY
    weight: float = 1.0


class ProvenanceTree(BaseModel):
    """Tracks the lineage of every claim, query, hit, page, passage, and verdict."""

    nodes: dict[str, ProvenanceNode] = Field(default_factory=dict)
    edges: list[ProvenanceEdge] = Field(default_factory=list)

    def add_node(self, node: ProvenanceNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: ProvenanceEdge) -> None:
        self.edges.append(edge)

    def path_for_citation(self, passage_id: str) -> list[ProvenanceNode]:
        """Return the provenance path for a passage citation."""
        result: list[ProvenanceNode] = []
        current = self.nodes.get(passage_id)
        if current is None:
            for node in self.nodes.values():
                if node.ref_id == passage_id:
                    current = node
                    break
        if current is None:
            return result
        reverse_edges: dict[str, list[str]] = {}
        for edge in self.edges:
            reverse_edges.setdefault(edge.dst, []).append(edge.src)
        cursor: ProvenanceNode | None = current
        visited: set[str] = set()
        chain: list[ProvenanceNode] = []
        while cursor is not None and cursor.id not in visited:
            visited.add(cursor.id)
            chain.append(cursor)
            parents = reverse_edges.get(cursor.id, [])
            cursor = self.nodes.get(parents[0]) if parents else None
        chain.reverse()
        return chain

    def sources_for_claim(self, claim_id: str) -> list[ProvenanceNode]:
        """Return source nodes for a claim."""
        direct_matches = [
            n for n in self.nodes.values() if n.ref_id == claim_id
        ]
        claim_node_ids = {
            node.id
            for node in self.nodes.values()
            if node.node_type == "claim" and node.ref_id == claim_id
        }
        if not claim_node_ids:
            return direct_matches
        reachable: set[str] = set(claim_node_ids)
        queue = list(claim_node_ids)
        while queue:
            current = queue.pop(0)
            for edge in self.edges:
                if edge.src == current and edge.dst not in reachable:
                    reachable.add(edge.dst)
                    queue.append(edge.dst)
        derived_sources = [
            self.nodes[node_id]
            for node_id in reachable
            if node_id in self.nodes
            and self.nodes[node_id].node_type in {"hit", "page", "passage"}
        ]
        return derived_sources or direct_matches


# ─── Workflow Models ──────────────────────────────────────────────────────────


@dataclass
class BudgetConsumption:
    """Multi-dimensional budget tracking."""

    rounds: int = 0
    tokens_consumed: int = 0
    wall_seconds: float = 0.0
    http_calls: int = 0
    urls_fetched: int = 0
    critic_revision_loops: int = 0

    def is_exhausted(self, budget: WorkflowBudget) -> bool:
        return (
            self.rounds >= budget.max_rounds
            or self.tokens_consumed >= budget.max_tokens
            or self.wall_seconds >= budget.max_wall_seconds
            or self.http_calls >= budget.max_http_calls
            or self.critic_revision_loops >= budget.max_critic_revision_loops
        )


@dataclass
class NoveltyTracker:
    """Tracks novelty of evidence across rounds."""

    new_unique_hits: int = 0
    new_unique_pages: int = 0
    new_supporting_evidence_spans: int = 0
    new_independent_publishers: int = 0

    @property
    def marginal_gain(self) -> int:
        return (
            self.new_unique_hits
            + self.new_unique_pages
            + self.new_supporting_evidence_spans
            + 2 * self.new_independent_publishers
        )


@dataclass
class RetryPolicy:
    """Retry configuration for agent calls."""

    max_attempts: int = 3
    backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 60.0


@dataclass
class AgentDefinition:
    """Runtime contract for an agent role."""

    role: AgentRole
    capabilities: set[AgentCapability] = field(default_factory=set)
    input_schema: type[BaseModel] | None = None
    output_schema: type[BaseModel] | None = None
    url_env_var: str = ""
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    circuit_breaker: CircuitBreakerConfig | None = None


class WorkflowBudget(BaseModel):
    """Budget constraints for the workflow."""

    max_rounds: int = 5
    max_tokens: int = 200000
    max_wall_seconds: float = 180.0
    max_http_calls: int = 50
    max_urls_fetched: int = 20
    min_marginal_evidence: int = 2
    max_critic_revision_loops: int = 2


# ─── Legacy / UI Models ───────────────────────────────────────────────────────


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


class ResearchSession(BaseModel):
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
        return self.agent_results.get(role, AgentResult(role=role))

    def ensure_agent_results(self) -> None:
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


# ─── FactChecker Output ───────────────────────────────────────────────────────


class FactCheckerOutput(BaseModel):
    """Output contract for the FactChecker agent."""

    updated_claim_state: ClaimState = Field(default_factory=ClaimState)
    claim_follow_ups: list[ClaimFollowUp] = Field(default_factory=list)
    budget_consumed: BudgetConsumption = Field(
        default_factory=BudgetConsumption
    )
    replan_reasons: list[ReplanReason] = Field(default_factory=list)
    stale_dependents: list[str] = Field(default_factory=list)
    cached_verifications: list[str] = Field(default_factory=list)

    @property
    def needs_replan(self) -> bool:
        return bool(self.replan_reasons)

    @property
    def tentatively_supported_claim_ids(self) -> list[str]:
        return [
            cid
            for cid, v in self.updated_claim_state.verification.items()
            if v.verdict == Verdict.SUPPORTED
            and v.adversary_result == "NOT_RUN"
        ]
