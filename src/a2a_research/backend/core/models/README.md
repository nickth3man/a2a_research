# Models

Pydantic domain models shared across agents, workflow, and UI. This directory is the single source of truth for structured data in the research pipeline.

## File Overview

| File | Purpose |
|------|---------|
| `enums.py` | Shared enumeration types |
| `claims.py` | Claim decomposition, DAG, and replanning |
| `evidence.py` | Evidence units, passages, and source independence |
| `verification.py` | Claim verification state and aggregated tracking |
| `reports.py` | Structured report output, sections, and citations |
| `session.py` | Research session state and agent results |
| `workflow.py` | Workflow configuration, budgets, and runtime policies |
| `provenance.py` | Provenance tree for claim-to-source lineage |
| `fact_checker.py` | FactChecker agent output contract |
| `__init__.py` | Central re-exports of all public models |

## Model Groupings

### Enumerations (`enums.py`)

Shared `StrEnum` constants used across the system:

- **Verdict** — `SUPPORTED`, `REFUTED`, `MIXED`, `UNRESOLVED`, `STALE`, `INSUFFICIENT_EVIDENCE`, `NEEDS_MORE_EVIDENCE`
- **AgentRole** — named pipeline participants (`PLANNER`, `SEARCHER`, `FACT_CHECKER`, `SYNTHESIZER`, etc.)
- **AgentCapability** — what an agent can do (`DECOMPOSE`, `SEARCH`, `VERIFY`, `SYNTHESIZE`, etc.)
- **AgentStatus** / **TaskStatus** — execution lifecycle states
- **ReplanReasonCode** — why the Planner should replan (`TOO_BROAD`, `MISSING_CLAIM`, etc.)
- **ProvenanceEdgeType** — edge labels in the provenance graph

### Claims (`claims.py`)

Core claim models and operations:

- **Claim** — immutable claim as decomposed by the Planner, with freshness requirements and legacy confidence fields
- **FreshnessWindow** — per-claim recency requirement
- **ClaimDependency** — edge in the claim DAG (`presupposes`, `refines`, `contrasts`)
- **ClaimDAG** — acyclic dependency graph over claims with topological sort and descendant queries
- **ClaimFollowUp** — follow-up query for iterative evidence gathering
- **ReplanReason** — structured reason for Planner replanning

### Evidence (`evidence.py`)

Evidence collection and source tracking:

- **Passage** — extracted passage with claim relevance scores and quotation flag
- **CredibilitySignals** — domain reputation, author verification, citations, content age
- **EvidenceUnit** — normalized evidence with stable IDs, source type, publisher info, and quoted passages
- **IndependenceGraph** — tracks independent vs syndicated sources per claim

### Verification (`verification.py`)

Claim verification state management:

- **ClaimVerification** — mutable verification state for a single claim (verdict, confidence, evidence IDs, adversary result)
- **VerificationRevision** — audit record of a verdict change
- **ClaimState** — aggregated state for all claims in a session, including DAG, resolution lists, and stale-cascade logic

### Reports (`reports.py`)

Structured report generation:

- **WebSource** — URL-level citation with title and excerpt
- **Citation** — inline citation attached to a report section
- **ReportSection** — heading, body, and citations
- **ReportOutput** — final structured report with `to_markdown()` rendering

### Session (`session.py`)

Pipeline state and results:

- **AgentResult** — result of a single agent execution (role, status, claims, raw content)
- **ResearchSession** — full session state across all stages, including claims, evidence, provenance, budget, and formatted outputs
- **default_roles()** / **workflow_v2_roles()** — standard pipeline role orderings

### Workflow (`workflow.py`)

Orchestration configuration:

- **WorkflowBudget** — multi-dimensional budget constraints (rounds, tokens, time, HTTP calls)
- **BudgetConsumption** — current consumption against a budget
- **NoveltyTracker** — novelty of evidence across rounds, with a weighted marginal gain score
- **RetryPolicy** — retry and backoff settings for agent calls
- **CircuitBreakerConfig** — circuit breaker thresholds
- **AgentDefinition** — runtime contract for a role (capabilities, schemas, URL, retry, circuit breaker)

### Provenance (`provenance.py`)

Lineage tracking:

- **ProvenanceNode** — node in the provenance tree (claim, query, hit, page, passage, verdict, challenge)
- **ProvenanceEdge** — directed edge with type and weight
- **ProvenanceTree** — full lineage graph with path-for-citation and sources-for-claim lookups

### FactChecker (`fact_checker.py`)

- **FactCheckerOutput** — structured output contract for the LangGraph-based FactChecker, including updated claim state, follow-ups, budget consumed, and replan reasons

## Consumers

These models are imported by:

- `agents/` — per-agent I/O and session mutation
- `workflow/` — top-level orchestrator state
- `a2a/` — A2A client payloads, cards, and task helpers
- `ui/` — Mesop `@stateclass` fields (nested models are kept concrete for Mesop serialization)
