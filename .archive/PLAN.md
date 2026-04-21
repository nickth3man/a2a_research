# Workflow Architecture: Configurable Multi-Agent Research Pipeline

## 1. Philosophy

The coordinator is a **workflow engine**, not a hardcoded script. Agents are **role-based plugins** connected by a **declarative flow graph**. The graph supports:

- **Sequential steps** (Preprocess → Clarify → Plan → loop → Synthesize)
- **Claim-centric loops** built on a **claim-dependency DAG**, not a flat list
- **Conditional branching** (skip Synthesizer if all claims refuted, replan if decomposition wrong)
- **Budget-aware termination** (rounds, tokens, time, novelty, oscillation)
- **Checkpointing** (persist state after each stage for resumability)
- **Dynamic insertion** (add Critic, Ranker, Adversary, QueryExpander agents)
- **Adversarial verification** (Devil's Advocate agent required before `SUPPORTED`)
- **Source-independence accounting** (confidence derived from independent sources, not raw evidence count)

All inter-agent communication uses the A2A HTTP protocol with structured envelopes carrying `session_id`, `trace_id`, and `span_id`. The coordinator owns session state, budget tracking, timeout handling, checkpointing, and progress event emission.

---

## 2. Agent Role Definition

Each agent declares its **capabilities** and **I/O contract**. The coordinator validates connections and marshals payloads at workflow load time.

### 2.1 Role Schema

```python
class AgentCapability(StrEnum):
    """What an agent can do."""
    PREPROCESS = "preprocess"           # Classify / sanitize / PII scan
    CLARIFY = "clarify"                 # Disambiguate underspecified queries
    DECOMPOSE = "decompose"             # Break query into claims + DAG edges + seed queries
    REPLAN = "replan"                   # Revise claims mid-loop with structured reason codes
    SEARCH = "search"                   # Execute web search, return hits
    RANK = "rank"                       # Score hits by claim relevance / credibility / freshness
    EXTRACT = "extract"                 # Fetch and extract page content
    NORMALIZE = "normalize"             # Chunk, dedupe, assign stable IDs, compute source independence
    VERIFY = "verify"                   # Check claims against evidence
    ADVERSARIAL_VERIFY = "adversarial_verify"   # Actively seek counter-evidence
    FOLLOW_UP = "follow_up"             # Generate per-claim follow-up queries
    SYNTHESIZE = "synthesize"           # Produce final report
    CRITIQUE = "critique"               # Evaluate report quality
    POSTPROCESS = "postprocess"         # Render citations, redact PII, format outputs

class AgentRole(StrEnum):
    """Named pipeline participants."""
    PREPROCESSOR = "preprocessor"
    CLARIFIER = "clarifier"                     # NEW: disambiguation stage
    PLANNER = "planner"
    SEARCHER = "searcher"                       # Multi-provider ensemble (Tavily+Brave+DDG)
    RANKER = "ranker"                           # Freshness-aware scoring
    READER = "reader"
    EVIDENCE_DEDUPLICATOR = "evidence_deduplicator"  # Adds source-independence accounting
    FACT_CHECKER = "fact_checker"
    ADVERSARY = "adversary"                     # NEW: Devil's Advocate / counter-evidence
    SYNTHESIZER = "synthesizer"
    CRITIC = "critic"
    POSTPROCESSOR = "postprocessor"

@dataclass
class AgentDefinition:
    """Runtime contract for an agent role."""
    role: AgentRole
    capabilities: set[AgentCapability]
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    url_env_var: str
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    circuit_breaker: CircuitBreakerConfig | None = None
```

### 2.2 Agent Definitions

| Role | Capabilities | Input | Output | URL Env |
|------|-------------|-------|--------|---------|
| **Preprocessor** | `PREPROCESS` | `query: str` | `sanitized_query`, `query_class`, `pii_findings`, `domain_hints` | PREPROCESSOR_URL |
| **Clarifier** | `CLARIFY` | `query: str`, `query_class` | `clarifications: list[Disambiguation]`, `committed_interpretation: str`, `audit_note: str` | CLARIFIER_URL |
| **Planner** | `DECOMPOSE`, `REPLAN` | `query: str`, `interpretation`, `domain_hints`, `replan_reasons?` | `original_claims: list[Claim]`, `claim_dag: ClaimDAG`, `seed_queries: list[str]` | PLANNER_URL |
| **Searcher** | `SEARCH` | `queries: list[str]`, `freshness_hint?`, `budget: SearchBudget` | `hits: list[WebHit]`, `providers_used: list[str]` | SEARCHER_URL |
| **Ranker** | `RANK` | `hits: list[WebHit]`, `unresolved_claims: list[Claim]`, `freshness_windows: dict[claim_id, window]` | `ranked_urls`, `credibility_scores`, `freshness_scores`, `selection_rationale` | RANKER_URL |
| **Reader** | `EXTRACT` | `urls`, `claims`, `fetch_budget` | `pages: list[PageContent]`, `failed_urls`, `injection_flags` | READER_URL |
| **EvidenceDeduplicator** | `NORMALIZE` | `pages`, `existing_evidence` | `evidence_units`, `dedupe_stats`, `independence_graph` | EVIDENCE_DEDUPLICATOR_URL |
| **FactChecker** | `VERIFY`, `FOLLOW_UP` | `query`, `claim`, `claim_dag`, `evidence`, `budget` | `updated_claim_state`, `claim_follow_ups`, `budget_consumed`, `replan_reasons`, `stale_dependents` | FACT_CHECKER_URL |
| **Adversary** | `ADVERSARIAL_VERIFY` | `claim`, `tentative_verdict`, `evidence` | `counter_evidence_queries`, `counter_evidence_refs`, `challenge_result: {HOLDS, WEAKENED, REFUTED}` | ADVERSARY_URL |
| **Synthesizer** | `SYNTHESIZE` | `query`, `claim_state`, `evidence`, `provenance_tree`, `tentative_report?` | `report`, `reasoning_trace` | SYNTHESIZER_URL |
| **Critic** | `CRITIQUE` | `report`, `claim_state`, `evidence` | `critique`, `suggested_improvements`, `iteration_count` | CRITIC_URL |
| **Postprocessor** | `POSTPROCESS` | `report`, `claim_state`, `provenance_tree`, `output_formats`, `citation_style` | `formatted_outputs` | POSTPROCESSOR_URL |

---

## 3. Core Data Models

### 3.1 Claim State (Immutable Original + Mutable State + Dependency DAG)

```python
class FreshnessWindow(BaseModel):
    """Per-claim recency requirement."""
    max_age_days: int | None        # None = no recency requirement
    strict: bool = False            # If True, evidence older than window is rejected outright
    rationale: str

class Claim(BaseModel):
    """Immutable claim as originally decomposed by Planner."""
    id: str
    text: str
    freshness: FreshnessWindow
    created_at: datetime

class ClaimDependency(BaseModel):
    """Edge in the claim DAG: `child` presupposes `parent`."""
    parent_id: str
    child_id: str
    relation: Literal["presupposes", "refines", "contrasts"]

class ClaimDAG(BaseModel):
    """Acyclic dependency graph over claims."""
    nodes: list[str]                # claim_ids
    edges: list[ClaimDependency]

    def parents_of(self, claim_id: str) -> list[str]: ...
    def descendants_of(self, claim_id: str) -> list[str]: ...
    def topological_order(self) -> list[str]: ...

class ClaimVerification(BaseModel):
    """Mutable verification state for a claim."""
    claim_id: str
    verdict: Literal["SUPPORTED", "REFUTED", "MIXED", "UNRESOLVED", "STALE"]
    confidence: float               # Derived from independent sources, not raw evidence count
    independent_source_count: int   # Distinct operators/owners after syndication collapse
    supporting_evidence_ids: list[str]
    refuting_evidence_ids: list[str]
    contradictions: list[str]
    adversary_result: Literal["HOLDS", "WEAKENED", "REFUTED", "NOT_RUN"] = "NOT_RUN"
    revision_history: list[VerificationRevision]
    last_updated: datetime

class ClaimState(BaseModel):
    """Aggregated verification state for all claims."""
    original_claims: list[Claim]
    dag: ClaimDAG
    verification: dict[str, ClaimVerification]
    unresolved_claim_ids: list[str]
    stale_claim_ids: list[str]       # Dependents of a claim whose verdict just changed
    resolved_claim_ids: list[str]

    def mark_dependents_stale(self, parent_id: str) -> None:
        """Cascade STALE to descendants when a parent verdict flips."""
        for descendant in self.dag.descendants_of(parent_id):
            self.verification[descendant].verdict = "STALE"
            self.stale_claim_ids.append(descendant)

    @property
    def all_resolved(self) -> bool:
        return not self.unresolved_claim_ids and not self.stale_claim_ids
```

### 3.2 Evidence Model (Stable IDs + Independence Graph)

```python
class EvidenceUnit(BaseModel):
    id: str                         # Hash of URL + content fingerprint
    url: str
    canonical_url: str
    title: str
    source_type: Literal["academic", "news", "blog", "wiki", "forum", "social", "other"]
    domain_authority: float         # 0.0-1.0, backed by Tranco + curated overrides
    publisher_id: str               # Owner/operator identifier (for syndication collapse)
    syndication_cluster_id: str | None   # Null if unique; otherwise shared across duplicates
    published_at: datetime | None
    fetched_at: datetime
    content_hash: str
    main_text: str
    quoted_passages: list[Passage]
    credibility_signals: CredibilitySignals

class IndependenceGraph(BaseModel):
    """Tracks independent vs syndicated sources per claim."""
    claim_to_publishers: dict[str, set[str]]             # claim_id -> {publisher_id}
    syndication_clusters: dict[str, list[str]]           # cluster_id -> [evidence_ids]
    citation_chains: dict[str, list[str]]                # evidence_id -> [cited_evidence_ids]

    def independent_source_count(self, claim_id: str) -> int:
        """Distinct publishers after collapsing syndication clusters."""
        ...

class Passage(BaseModel):
    id: str
    evidence_id: str
    text: str
    claim_relevance_scores: dict[str, float]
    is_quotation: bool

class CredibilitySignals(BaseModel):
    domain_reputation: float
    author_verified: bool
    has_citations: bool
    content_freshness_days: int | None
```

### 3.3 Per-Claim Follow-Up

```python
class ClaimFollowUp(BaseModel):
    claim_id: str
    claim_text: str
    reason: str
    queries: list[str]
    priority: Literal["high", "medium", "low"]
    suggested_sources: list[str]
    adversarial: bool = False       # True when queries are counter-evidence probes
```

### 3.4 Strongly Typed Verdicts and Structured Replan Reasons

```python
class Verdict(BaseModel):
    label: Literal["SUPPORTED", "REFUTED", "MIXED", "UNRESOLVED", "STALE"]
    confidence: float
    evidence_ids: list[str]
    contradictions: list[str]
    reasoning: str

class ReplanReasonCode(StrEnum):
    TOO_BROAD = "too_broad"
    TOO_NARROW = "too_narrow"
    MISSING_CLAIM = "missing_claim"
    REDUNDANT_CLAIM = "redundant_claim"
    WRONG_DOMAIN = "wrong_domain"
    AMBIGUOUS_TERM = "ambiguous_term"

class ReplanReason(BaseModel):
    code: ReplanReasonCode
    claim_id: str | None            # None when suggesting a new claim
    detail: str
    suggested_action: Literal["split", "merge", "drop", "add", "rephrase"]
```

### 3.5 Provenance Tree Schema

```python
class ProvenanceEdgeType(StrEnum):
    CLAIM_TO_QUERY = "claim_to_query"
    QUERY_TO_HIT = "query_to_hit"
    HIT_TO_PAGE = "hit_to_page"
    PAGE_TO_PASSAGE = "page_to_passage"
    PASSAGE_TO_VERDICT = "passage_to_verdict"
    PASSAGE_TO_ADVERSARY_CHALLENGE = "passage_to_adversary_challenge"

class ProvenanceNode(BaseModel):
    id: str
    node_type: Literal["claim", "query", "hit", "page", "passage", "verdict", "challenge"]
    ref_id: str                     # Points at Claim.id, query hash, WebHit.id, EvidenceUnit.id, Passage.id, etc.
    metadata: dict[str, Any]

class ProvenanceEdge(BaseModel):
    src: str                        # ProvenanceNode.id
    dst: str
    edge_type: ProvenanceEdgeType
    weight: float = 1.0

class ProvenanceTree(BaseModel):
    nodes: dict[str, ProvenanceNode]
    edges: list[ProvenanceEdge]

    def path_for_citation(self, passage_id: str) -> list[ProvenanceNode]: ...
    def sources_for_claim(self, claim_id: str) -> list[ProvenanceNode]: ...
```

---

## 4. Flow Graph

### 4.1 Target Flow (v2.2 — Claim-DAG, Clarified, Adversarial, Source-Independent)

The v2.2 pipeline extends v2.1 with:

1. A **Clarifier** stage that commits to a single interpretation for ambiguous queries and records an audit note.
2. A **claim-dependency DAG** emitted by the Planner; verdict changes cascade `STALE` to dependents.
3. An **Adversary** stage required to promote any tentatively `SUPPORTED` claim through a counter-evidence pass.
4. **Source-independence accounting** so confidence derives from distinct publishers, not raw evidence count.
5. **Structured replan reasons** so the Planner acts surgically rather than re-decomposing from scratch.
6. **Freshness windows** set per-claim by the Planner and honored by the Ranker.
7. An **oscillation guard** on the Critic loop-back.
8. **Defense-in-depth PII redaction** at query-egress, evidence-ingest, checkpoint-write, and pre-synthesis.
9. **Distributed trace identifiers** (`session_id`, `trace_id`, `span_id`) on every A2A envelope.

```yaml
workflow:
  version: "2.2"
  name: claim_centric_research

  protocol:
    a2a_envelope:
      required: [message_id, correlation_id, session_id, trace_id, span_id, timestamp, retry_count]
      optional: [chunk_sequence]                        # used by streaming synthesis (SSE via coordinator)
      error_payload: AgentError
    capability_negotiation: true
    schema_version_conflict: hot_migrate_via_registry   # fallback: downgrade; final fallback: abort
    agent_discovery: env_registry_then_static_config    # Consul/k8s integration deferred until multi-host
    direct_agent_sse: disallowed                        # streaming must proxy through the coordinator

  budget:
    max_rounds: 5
    max_tokens: 200000
    max_wall_seconds: 180
    max_http_calls: 50
    max_urls_fetched: 20
    min_marginal_evidence: 2
    max_critic_revision_loops: 2          # oscillation guard
    per_stage_timeouts:
      preprocessor: 10s
      clarifier: 15s
      planner: 20s
      searcher: 15s
      ranker: 5s
      reader: 30s
      evidence_deduplicator: 10s
      fact_checker: 45s
      adversary: 30s
      synthesizer: 60s
      critic: 30s
      postprocessor: 10s

  trust_safety:
    domain_policy: hybrid_blocklist_with_curated_allowlist  # blocklist default, allowlist boosts ranking
    blocklist: default_unsafe
    robots_txt: respect_disallow_block_unless_research_mode # research_mode requires per-session enablement by an authenticated operator
    ssrf_protection: always_on                              # no per-session override
    content_type_allow: [text/html, application/pdf, text/plain]
    prompt_injection_defense: fence_untrusted_text
    reputation_source: tranco_top_1m + curated_overrides
    pii_redaction:
      query_egress: hash_with_session_key
      evidence_ingest: mask
      checkpoint_write: mask
      pre_synthesis: mask

  cache:
    search:    { ttl: 4h,  key: "(query_hash, provider, freshness_bucket)" }
    page:      { ttl: 7d,  key: "(url_hash)", revalidate: etag_or_last_modified }
    verify:    { ttl: 30d, key: "(claim_text_hash_post_replan, evidence_content_hash)", invalidate_on_page_revalidation: true }
    workflow:  { ttl: until_completion, key: "(session_id, stage)" }
    replay:    { mode: hash_and_reconstruct, record: [urls, claims, verdicts, adversary_challenges] }

  stages:
    # ─────────────── Pre-flight ───────────────
    - name: preprocess
      agent: preprocessor
      input:
        query: "$.query"
      output:
        sanitized_query: "$.preprocess.sanitized_query"
        query_class: "$.preprocess.class"
        query_class_confidence: "$.preprocess.class_confidence"
        pii_findings: "$.preprocess.pii"
        domain_hints: "$.preprocess.domain_hints"
      next:
        - condition: "$.preprocess.class == 'unanswerable' AND $.preprocess.class_confidence > 0.8"
          stage: abort
        - condition: "$.preprocess.class == 'sensitive' AND not $.config.allow_sensitive"
          stage: abort
        - condition: default
          stage: clarify
      on_failure: continue                  # default to factual

    - name: clarify
      agent: clarifier
      input:
        query: "$.preprocess.sanitized_query"
        query_class: "$.preprocess.class"
      output:
        disambiguations: "$.clarifier.disambiguations"
        committed_interpretation: "$.clarifier.committed_interpretation"
        audit_note: "$.clarifier.audit_note"
      next: plan
      on_failure: continue                  # treat original query as the interpretation

    - name: plan
      agent: planner
      checkpoint: true
      input:
        query: "$.clarifier.committed_interpretation"
        domain_hints: "$.preprocess.domain_hints"
      output:
        original_claims: "$.planner.original_claims"
        claim_dag: "$.planner.claim_dag"
        seed_queries: "$.planner.seed_queries"
      next: dedupe_seed_queries
      on_failure: abort

    - name: dedupe_seed_queries
      type: utility
      op: semantic_query_dedupe
      input:
        queries: "$.planner.seed_queries"
      params:
        embedding_model: "$.config.embedding_model"
        cosine_threshold: 0.9
        scope: within_claim_only              # safer: preserves claim-specific phrasing
      output:
        deduped_queries: "$.loop.claim_queries"
      next: gather_evidence

    # ─────────────── Claim-centric loop (DAG-aware) ───────────────
    - name: gather_evidence
      type: claim_centric_loop
      budget: inherit
      entry: search
      traversal: dag_topological             # process parents before dependents

      until:
        - "$.claim_state.all_resolved"
        - "$.loop.budget_exhausted"
        - "$.loop.novelty.marginal_gain < budget.min_marginal_evidence"
        - "len($.loop.deduplicated_follow_ups) == 0"

      accumulator:
        evidence_units: "$.evidence_deduplicator.new_evidence"
        claim_state: "$.fact_checker.updated_claim_state"
        independence_graph: "$.evidence_deduplicator.independence_graph"
        novelty: "$.loop.novelty_tracker"
        provenance_tree: "$.loop.provenance_tree"

      stages:
        - name: search
          type: cache_then_call
          cache: search
          call:
            type: parallel
            branches:
              - agent: searcher_tavily
              - agent: searcher_brave
              - agent: searcher_ddg
            shared_input:
              queries: "$.loop.claim_queries"
              freshness_hints: "$.claim_state.freshness_windows"
              budget: "$.loop.remaining_budget"
            merge: union_dedupe_by_url
          output:
            hits: "$.searcher.hits"
            providers_used: "$.searcher.providers_used"
            cache_hits: "$.cache.search.hits"
          next: rank
          on_failure: continue

        - name: rank
          agent: ranker
          input:
            hits: "$.searcher.hits"
            unresolved_claims: "$.claim_state.unresolved_or_stale_claims"
            freshness_windows: "$.claim_state.freshness_windows"
            budget: "$.loop.remaining_budget"
          output:
            ranked_urls: "$.ranker.ranked_urls"
            credibility_scores: "$.ranker.credibility"
            freshness_scores: "$.ranker.freshness"
            selection_rationale: "$.ranker.rationale"
          next: trust_safety_filter
          on_failure: use_all_hits

        - name: trust_safety_filter
          type: utility
          op: apply_trust_safety
          input:
            urls: "$.ranker.ranked_urls"
            policy: "$.workflow.trust_safety"
          output:
            allowed_urls: "$.safety.allowed_urls"
            rejected: "$.safety.rejected"
          next: read

        - name: read
          type: cache_then_call
          cache: page
          call:
            agent: reader
            input:
              urls: "$.safety.allowed_urls[:$.config.fetch_budget]"
              claims: "$.claim_state.unresolved_or_stale_claims"
              fetch_budget: "$.loop.remaining_fetch_budget"
          output:
            pages: "$.reader.pages"
            failed_urls: "$.reader.failed_urls"
            injection_flags: "$.reader.injection_flags"
          next: normalize
          on_failure: continue_with_partial

        - name: normalize
          agent: evidence_deduplicator
          input:
            pages: "$.reader.pages"
            existing_evidence: "$.accumulated.evidence_units"
            existing_independence_graph: "$.accumulated.independence_graph"
          output:
            new_evidence: "$.evidence_deduplicator.new_evidence"
            dedupe_stats: "$.evidence_deduplicator.stats"
            independence_graph: "$.evidence_deduplicator.independence_graph"
          next: verify

        - name: verify
          type: parallel_map
          over: "$.claim_state.unresolved_or_stale_claims_in_dag_order"
          cache: verify
          agent: fact_checker
          merge: crdt_union_per_claim_isolated_verdicts
          input:
            query: "$.query"
            claim: "$.item"
            claim_dag: "$.claim_state.dag"
            new_evidence: "$.evidence_deduplicator.new_evidence"
            accumulated_evidence: "$.accumulated.evidence_units"
            independence_graph: "$.accumulated.independence_graph"
            budget: "$.loop.remaining_budget"
          output:
            updated_claim_state: "$.claim_state"
            claim_follow_ups: "$.fact_checker.claim_follow_ups"
            budget_consumed: "$.fact_checker.budget_consumed"
            replan_reasons: "$.fact_checker.replan_reasons"
            stale_dependents: "$.fact_checker.stale_dependents"
            cached_verifications: "$.fact_checker.cached_verifications"
          next: adversary_gate
          on_failure: use_previous_state

        # ----- Adversary / Devil's Advocate pass -----
        - name: adversary_gate
          type: parallel_map
          over: "$.claim_state.tentatively_supported_claims"
          agent: adversary
          input:
            claim: "$.item"
            tentative_verdict: "$.claim_state.verification[$.item.id]"
            evidence: "$.accumulated.evidence_units"
            independence_graph: "$.accumulated.independence_graph"
          output:
            counter_evidence_queries: "$.adversary.counter_evidence_queries"
            counter_evidence_refs: "$.adversary.counter_evidence_refs"
            challenge_result: "$.adversary.challenge_result"
          post:
            - op: apply_adversary_result
              rules:
                HOLDS:     "$.claim_state.verification[$.item.id].verdict = 'SUPPORTED'"
                WEAKENED:  "$.claim_state.verification[$.item.id].verdict = 'MIXED'"
                REFUTED:   "$.claim_state.verification[$.item.id].verdict = 'REFUTED'; $.claim_state.mark_dependents_stale($.item.id)"
          next: snapshot
          on_failure: conservative_demote_to_mixed

        - name: snapshot
          agent: synthesizer
          mode: tentative
          input:
            query: "$.query"
            claim_state: "$.claim_state"
            evidence: "$.accumulated.evidence_units"
            provenance_tree: "$.accumulated.provenance_tree"
          output:
            tentative_report: "$.snapshots.latest"
          schedule:
            strategy: cheap_template_every_round_plus_full_on_exit
          next:
            - condition: "$.fact_checker.replan_reasons | any"
              stage: replan
            - condition: default
              stage: loop_end
          on_failure: continue

    - name: replan
      agent: planner
      mode: surgical
      input:
        original_query: "$.query"
        current_claims: "$.claim_state.original_claims"
        current_dag: "$.claim_state.dag"
        replan_reasons: "$.fact_checker.replan_reasons"
      output:
        revised_claims: "$.planner.original_claims"
        revised_dag: "$.planner.claim_dag"
        replan_queries: "$.loop.claim_queries"
      post:
        - op: preserve_unchanged_evidence        # only invalidate verify cache for touched claims
      next: gather_evidence
      on_failure: abort_with_partial

    # ─────────────── Final synthesis & critique ───────────────
    - name: synthesize
      agent: synthesizer
      checkpoint: true
      streaming: "$.config.streaming"            # SSE from coordinator, proxying agent stream via A2A chunked frames
      input:
        query: "$.query"
        claim_state: "$.claim_state"
        evidence: "$.accumulated.evidence_units"
        provenance_tree: "$.accumulated.provenance_tree"
        tentative_report: "$.snapshots.latest"
      output:
        report: "$.report"
        reasoning_trace: "$.synthesizer.reasoning"
      next: critique
      on_failure: degraded_claims_only

    - name: critique
      agent: critic
      input:
        report: "$.report"
        claim_state: "$.claim_state"
        evidence: "$.accumulated.evidence_units"
      output:
        critique: "$.critique"
        improvements: "$.critique.suggested_improvements"
        iteration_count: "$.critique.iteration_count"
      next:
        - condition: "$.critique.passed"
          stage: postprocess
        - condition: "$.critique.iteration_count >= budget.max_critic_revision_loops"
          stage: postprocess_with_warnings       # oscillation guard forces exit
        - condition: "$.critique.needs_revision AND $.budget.remaining > threshold"
          stage: gather_evidence
        - condition: default
          stage: postprocess_with_warnings
      on_failure: postprocess

    # ─────────────── Postprocessing ───────────────
    - name: postprocess
      agent: postprocessor
      input:
        report: "$.report"
        claim_state: "$.claim_state"
        provenance_tree: "$.accumulated.provenance_tree"
        output_formats: "$.config.output_formats"         # markdown | json (PDF deferred)
        citation_style: "$.config.citation_style"         # numeric | author_year | hyperlinked_footnotes
      output:
        formatted_outputs: "$.outputs"
      next: done

    - name: postprocess_with_warnings
      agent: postprocessor
      input:
        report: "$.report"
        claim_state: "$.claim_state"
        warnings: "$.critique.warnings"
        provenance_tree: "$.accumulated.provenance_tree"
        output_formats: "$.config.output_formats"
        citation_style: "$.config.citation_style"
      output:
        formatted_outputs: "$.outputs"
      next: done_with_warnings

    # ─────────────── Terminals ───────────────
    - name: done
      type: terminal
      output:
        outputs: "$.outputs"
        claim_state: "$.claim_state"
        provenance: "$.accumulated.provenance_tree"

    - name: done_with_warnings
      type: terminal
      output:
        outputs: "$.outputs"
        warnings: "$.critique.warnings"
        unresolved_claims: "$.claim_state.unresolved_claim_ids"

    - name: abort
      type: terminal
      session_error: "Pipeline failed at {{ failed_stage }}"

    - name: abort_with_partial
      type: terminal
      session_error: "Replanning failed; partial results available"
      partial_output:
        tentative_report: "$.snapshots.latest"
        claim_state: "$.claim_state"
        evidence: "$.accumulated.evidence_units"

    - name: degraded_claims_only
      type: terminal
      session_error: "Synthesis failed; returning verified claims"
      partial_output:
        tentative_report: "$.snapshots.latest"
        claim_state: "$.claim_state"
```

### 4.2 Visual Diagram

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                  COORDINATOR                                       │
│  (A2A envelopes · session/trace/span IDs · capability negotiation · checkpoints · │
│   budget · cache · defense-in-depth PII redaction)                                │
│                                                                                    │
│  ┌──────────────┐  classify · sanitize · PII scan · confidence-aware fall-through │
│  │ PREPROCESSOR │── unanswerable/sensitive? ─▶ ABORT                              │
│  └──────────────┘                                                                 │
│         ▼                                                                          │
│  ┌──────────────┐                                                                 │
│  │  CLARIFIER   │── 1-3 disambiguations · commits single interpretation · audit   │
│  │    (NEW)     │                                                                 │
│  └──────────────┘                                                                 │
│         ▼                                                                          │
│  ┌──────────────┐                                                                 │
│  │   PLANNER    │── original_claims[] + claim_DAG + freshness_windows + seeds[]   │
│  └──────────────┘                                                                 │
│         ▼                                                                          │
│  ┌──────────────┐                                                                 │
│  │   SEMANTIC   │── within-claim cosine-dedupe → claim_queries[]                  │
│  │    DEDUP     │                                                                 │
│  └──────────────┘                                                                 │
│         ▼                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐    │
│  │            CLAIM-CENTRIC EVIDENCE LOOP (DAG topological order)             │    │
│  │  ┌────────────┐  cache_then_call · freshness_hint                          │    │
│  │  │   SEARCH   │── Parallel: Tavily + Brave + DDG (circuit-broken)          │    │
│  │  └────────────┘                                                            │    │
│  │         ▼                                                                  │    │
│  │  ┌────────────┐                                                            │    │
│  │  │   RANKER   │── relevance · credibility · freshness-per-claim · diversity│    │
│  │  └────────────┘                                                            │    │
│  │         ▼                                                                  │    │
│  │  ┌────────────┐                                                            │    │
│  │  │ TRUST &    │── blocklist · robots.txt · SSRF-always · content-type      │    │
│  │  │  SAFETY    │                                                            │    │
│  │  └────────────┘                                                            │    │
│  │         ▼                                                                  │    │
│  │  ┌────────────┐  cache_then_call (page, ETag revalidate)                   │    │
│  │  │   READER   │── fence injection · truncation flags                       │    │
│  │  └────────────┘                                                            │    │
│  │         ▼                                                                  │    │
│  │  ┌────────────┐                                                            │    │
│  │  │  DEDUPE/   │── stable IDs · canonical URLs · syndication collapse ·     │    │
│  │  │  NORMALIZE │   independence_graph (independent_source_count)            │    │
│  │  └────────────┘                                                            │    │
│  │         ▼                                                                  │    │
│  │  ┌────────────┐  parallel_map · CRDT-merged · verify cache                 │    │
│  │  │ FACT_CHECK │── claim_state{} · structured replan_reasons · stale_deps   │    │
│  │  └────────────┘                                                            │    │
│  │         ▼                                                                  │    │
│  │  ┌────────────┐  parallel_map over tentatively SUPPORTED claims            │    │
│  │  │ ADVERSARY  │── inversion queries · counter-experts · challenge_result   │    │
│  │  │   (NEW)    │   HOLDS → SUPPORTED · WEAKENED → MIXED · REFUTED → cascade │    │
│  │  └────────────┘                                                            │    │
│  │         ▼                                                                  │    │
│  │  ┌────────────┐  cheap-template every round · full synth only on exit     │    │
│  │  │ SNAPSHOT   │                                                            │    │
│  │  └────────────┘                                                            │    │
│  │         │                                                                  │    │
│  │         │ replan_reasons? ──▶ surgical REPLANNER (preserves evidence)     │    │
│  │         │ all resolved · budget · novelty · empty follow-ups ──▶ exit     │    │
│  │         └──────── loop back to SEARCH ──────────────────────────────────  │    │
│  └──────────────────────────────────────────────────────────────────────────┘    │
│         ▼                                                                          │
│  ┌──────────────┐    ┌──────────────┐ iter_count ≥ 2 ──▶ POSTPROCESS_WITH_WARN   │
│  │ SYNTHESIZER  │───▶│    CRITIC    │ passed ──▶ POSTPROCESS ──▶ DONE            │
│  │ (streaming   │    │              │ needs work ∧ budget ──▶ loop back          │
│  │  optional)   │    │              │                                            │
│  └──────────────┘    └──────────────┘                                            │
│         ▼                                                                          │
│  ┌──────────────┐                                                                 │
│  │ POSTPROCESS  │── citation rendering (numeric/author-year/footnotes) ·         │
│  │              │   PII redaction · markdown/json (PDF deferred)                 │
│  └──────────────┘                                                                 │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Loop Mechanics

### 5.1 DAG-Aware Claim-Centric Evidence Gathering

The loop traverses claims in **topological order** so parents resolve before dependents, and `STALE` cascades when a parent verdict changes:

```python
def claims_to_process(session: ResearchSession) -> list[Claim]:
    """Unresolved + STALE claims, sorted by DAG topological order."""
    order = session.claim_state.dag.topological_order()
    queue = []
    for claim_id in order:
        v = session.claim_state.verification[claim_id]
        if v.verdict in ("UNRESOLVED", "STALE"):
            parents = session.claim_state.dag.parents_of(claim_id)
            # Skip a claim if any parent is REFUTED — dependents are unreachable
            if any(session.claim_state.verification[p].verdict == "REFUTED" for p in parents):
                v.verdict = "STALE"
                continue
            queue.append(session.get_claim(claim_id))
    return queue
```

### 5.2 Budget Tracking (Multi-Dimensional + Oscillation)

```python
@dataclass
class BudgetConsumption:
    rounds: int = 0
    tokens_consumed: int = 0
    wall_seconds: float = 0.0
    http_calls: int = 0
    urls_fetched: int = 0
    critic_revision_loops: int = 0

    def is_exhausted(self, budget: Budget) -> bool:
        return (
            self.rounds >= budget.max_rounds
            or self.tokens_consumed >= budget.max_tokens
            or self.wall_seconds >= budget.max_wall_seconds
            or self.http_calls >= budget.max_http_calls
            or self.critic_revision_loops >= budget.max_critic_revision_loops
        )

@dataclass
class NoveltyTracker:
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
            + 2 * self.new_independent_publishers   # weight independence higher
        )
```

### 5.3 Loop Termination Conditions

The loop exits when **any** of:

1. `claim_state.all_resolved` (no UNRESOLVED, no STALE).
2. `budget.is_exhausted()` — includes critic oscillation ceiling.
3. `novelty.marginal_gain < budget.min_marginal_evidence`.
4. `len(deduplicated_follow_ups) == 0`.
5. `fact_checker.replan_reasons AND replan_failed`.

### 5.4 Evidence Accumulation, Deduplication, and Independence

Evidence units are append-only. Each ingestion:

```python
# Stable-ID dedupe
existing_ids = {e.id for e in session.accumulated_evidence}
new_evidence = [e for e in new_evidence if e.id not in existing_ids]
session.accumulated_evidence.extend(new_evidence)

# Syndication collapse: identical passages across publishers share a cluster_id;
# confidence counts distinct publishers, not cluster members.
session.independence_graph.update(new_evidence)

# Confidence = f(independent_source_count, credibility, adversary_result)
for claim_id in touched_claims:
    v = session.claim_state.verification[claim_id]
    v.independent_source_count = session.independence_graph.independent_source_count(claim_id)
    v.confidence = confidence_model(v)
```

### 5.5 Confidence Short-Circuit Rule

A claim with `confidence > 0.9` **and** `adversary_result == "HOLDS"` suppresses new follow-ups for that claim but is **still re-checked** if new evidence lands in a later round (verify cache makes this near-free).

### 5.6 Checkpointing

Checkpoint after: `plan`, `verify` (per round), `adversary_gate`, `synthesize`. Checkpoints are written through the PII-redaction pipeline (masked at checkpoint_write) and cached under `workflow:(session_id, stage)`.

---

## 6. FactChecker Contract (Claim-Centric, DAG-Aware)

```python
class FactCheckerOutput(BaseModel):
    updated_claim_state: ClaimState
    claim_follow_ups: list[ClaimFollowUp]
    budget_consumed: BudgetConsumption
    replan_reasons: list[ReplanReason] = []
    stale_dependents: list[str] = []                # claim_ids cascaded to STALE
    cached_verifications: list[str]

    @property
    def needs_replan(self) -> bool:
        return bool(self.replan_reasons)

    @property
    def tentatively_supported_claim_ids(self) -> list[str]:
        return [
            cid for cid, v in self.updated_claim_state.verification.items()
            if v.verdict == "SUPPORTED" and v.adversary_result == "NOT_RUN"
        ]
```

Tentatively `SUPPORTED` claims are **not final** until the Adversary stage upgrades them.

---

## 7. Progress Events (User-Meaningful)

```python
class ProgressEvent(BaseModel):
    session_id: str
    trace_id: str
    span_id: str
    timestamp: datetime

    phase: str                          # "preprocess" | "clarify" | "planning" | "evidence_gathering" | "adversary" | "synthesis" | "critique" | "postprocess"
    round: int
    stage: str

    total_claims: int
    resolved_claims: int
    unresolved_claims: int
    stale_claims: int
    tentatively_supported_claims: int

    evidence_units_total: int
    evidence_units_this_round: int
    independent_publishers_total: int

    budget_remaining: BudgetConsumption
    critic_revision_loops: int

    status_message: str
    detail: dict[str, Any]
```

**Event sequence example:**

```
[phase=preprocess] preprocessor_completed: class=factual (conf=0.91)
[phase=clarify] clarifier_committed: "best smartphone for mobile photography 2026"
[phase=planning] planner_completed: 5 claims, DAG: 3 roots + 2 dependents
[phase=evidence_gathering, round=1, stage=search] search_completed: 47 hits
[phase=evidence_gathering, round=1, stage=rank] rank_completed: freshness-weighted top 8 URLs
[phase=evidence_gathering, round=1, stage=normalize] normalize_completed: 6 pages → 12 evidence units, 4 independent publishers
[phase=evidence_gathering, round=1, stage=verify] verify_completed: 2 tentatively SUPPORTED, 3 UNRESOLVED
[phase=evidence_gathering, round=1, stage=adversary] adversary_completed: 2 challenges run → 1 HOLDS (SUPPORTED), 1 WEAKENED (MIXED)
[phase=evidence_gathering, round=1, stage=snapshot] snapshot_saved (cheap template)
[phase=evidence_gathering, round=2, ...] ...
[phase=evidence_gathering, round=3] loop_exited: reason=all_resolved
[phase=synthesis] synthesizer_completed
[phase=critique, iter=1] critique_completed: needs_revision
[phase=evidence_gathering, round=4] critic_loop_back
[phase=critique, iter=2] critique_completed: needs_revision → oscillation guard triggers postprocess_with_warnings
[phase=postprocess] outputs rendered: markdown + json
[phase=done] workflow_completed
```

---

## 8. Extensibility Patterns

### 8.1 Add QueryExpander

Insert between Planner and Searcher to generate query variants scoped within each claim (preserves claim-specific phrasing).

### 8.2 Replace Ranker with LearnedSourceRanker

Swap `ranker` for a learned model that ingests the feedback store (§9.4). Same capability (`RANK`), same I/O contract.

### 8.3 Parallel Verification per Claim

Already part of the target flow (`parallel_map`), merged via `crdt_union_per_claim_isolated_verdicts`: each claim's verdict is isolated, while evidence refs union across claims.

---

## 9. Error Handling, Degradation, and Feedback

### 9.1 Graded Fallback Modes

```yaml
degradation_policies:
  reader_partial_failure: { action: continue_with_partial }
  searcher_provider_failure: { action: accept_available_providers }
  adversary_failure: { action: conservative_demote_to_mixed }
  fact_checker_replan_failed: { action: abort_with_partial }
  synthesizer_failure: { action: emit_claims_markdown }
  budget_exhausted: { action: synthesize_partial_from_latest_snapshot }
  critic_oscillation: { action: postprocess_with_warnings }
```

### 9.2 Retry & Circuit Breaker

Applies to every agent with network I/O. Circuit-broken providers emit a progress event; the coordinator records the outage in the session and continues with remaining providers.

### 9.3 A2A Schema-Version Conflict

When capability negotiation detects a mid-session agent upgrade: **hot-migrate** via the `migrations/` registry if a migration exists for the version delta; otherwise **downgrade** to the previous schema for the session's lifetime; otherwise **abort** the session with a structured error. New sessions always use the latest schema.

### 9.4 User Feedback Loop

Thumbs-up/down on the final report is tied to `provenance_tree` node IDs. Feedback is stored in a dedicated `feedback_store` (SQLite single-tenant; shared Redis once multi-tenant). The Ranker team owns retraining from this store; retraining cadence is weekly offline with A/B rollout gated on the eval harness (§12 Phase 1).

---

## 10. Caching Strategy

### 10.1 Cache Layers

| Cache Key | TTL | Store | Invalidation |
|-----------|-----|-------|--------------|
| `search:(query_hash, provider, freshness_bucket)` | 4h (news: 1h) | SQLite local, Redis in multi-coordinator mode | Time-based |
| `page:(url_hash)` | 7 days | SQLite/Redis | ETag/Last-Modified revalidate |
| `verify:(claim_text_hash_post_replan, evidence_content_hash)` | 30 days | SQLite/Redis | Auto-invalidated when the upstream `page` cache entry revalidates with a new `content_hash`, or when a replan changes the claim text |
| `workflow:(session_id, stage)` | Until completion | SQLite | Completion or explicit resumption |

A daily background sweep reconciles orphaned `verify` entries whose upstream `page` or claim hash no longer exists.

### 10.2 SQLite vs Redis

**SQLite** is the default — covers single-coordinator deployments end-to-end. **Redis** is enabled by a single config flag (`cache.backend: redis`) once a second coordinator is deployed or cross-team verification-cache sharing is required. No code changes needed; the cache layer is backend-agnostic.

### 10.3 Replay

Replay mode is **hash-and-reconstruct**: store URLs, claim texts, verdicts, and adversary challenges; refetch pages via the `page` cache. Loses true determinism only if upstream pages change (acceptable — the replay then documents drift). Full-payload replay is explicitly out of scope.

---

## 11. Configuration

```yaml
workflow_config:
  version: "2.2"

  budget:
    max_rounds: 5
    max_tokens: 200000
    max_wall_seconds: 180
    max_http_calls: 50
    min_marginal_evidence: 2
    max_critic_revision_loops: 2

  search:
    providers: [tavily, brave, ddg]
    parallel: true
    max_results_per_provider: 5

  ranking:
    enabled: true
    fetch_budget: 8
    diversity_penalty: 0.3
    freshness_weight_default: 0.2        # per-claim override via FreshnessWindow

  evidence:
    deduplication: true
    chunk_size: 1000
    chunk_overlap: 200
    source_independence: enabled

  adversary:
    enabled: true
    trigger: on_tentative_supported
    inversion_query_count: 3
    counter_expert_lookup: enabled

  verification:
    cache_results: true
    confidence_auto_accept_threshold: 0.9
    short_circuit_when_adversary_holds: true

  synthesis:
    streaming: sse_via_coordinator        # A2A chunked frames end-to-end
    tentative_snapshot:
      strategy: cheap_template_every_round_plus_full_on_exit

  output:
    formats: [markdown, json]             # pdf deferred
    citation_style: hyperlinked_footnotes # default; overridable

  checkpointing:
    enabled: true
    stages: [plan, verify, adversary_gate, synthesize]

  pii:
    query_egress: hash_with_session_key
    evidence_ingest: mask
    checkpoint_write: mask
    pre_synthesis: mask

  telemetry:
    opentelemetry: true
    prometheus: true
    trace_log: true
    trace_ids: [session_id, trace_id, span_id]

  cost_attribution:
    enabled: true
    tags: [session_id, claim_id, user_id]   # propagated via A2A envelope now; cheap to add

  ab_testing:
    enabled: true
    sampling: per_query_class_sticky
    winner_metric: weighted_composite
    weights: { claim_recall: 0.35, citation_accuracy: 0.35, latency: 0.15, cost: 0.15 }
```

---

## 12. Implementation Roadmap

### Phase 1: Eval Harness + Core Claim State (Week 1)
- [ ] Build the **eval harness first**: 20-query golden set, manual scoring rubric (claim recall, citation accuracy, independence, adversary catch-rate), regression runner. Every later phase ships with a regression check.
- [ ] Implement `Claim`, `FreshnessWindow`, `ClaimDependency`, `ClaimDAG`, `ClaimVerification`, `ClaimState`.
- [ ] Update Planner to return `original_claims` + `claim_dag` + per-claim freshness.
- [ ] Update FactChecker to return `updated_claim_state` with DAG-aware cascading.

### Phase 2: Clarifier + Per-Claim Follow-Ups (Week 1–2)
- [ ] Implement Clarifier agent + disambiguation commit + audit note.
- [ ] Implement `ClaimFollowUp` (with `adversarial` flag).
- [ ] Searcher accepts per-claim freshness hints.
- [ ] Within-claim semantic query dedup.

### Phase 3: Budget, Novelty, Oscillation (Week 2)
- [ ] `BudgetConsumption`, `NoveltyTracker` (including `new_independent_publishers`).
- [ ] Oscillation guard via `max_critic_revision_loops`.
- [ ] Budget-exhaustion synthesis from latest snapshot.

### Phase 4: Ranking, Normalization, Source Independence (Week 3)
- [ ] Ranker with freshness + credibility + diversity.
- [ ] EvidenceDeduplicator with `IndependenceGraph`, syndication clusters, citation chains.
- [ ] Reader structured `PageContent` + injection flags.

### Phase 5: Parallel Search + Trust & Safety (Week 3)
- [ ] Parallel Tavily/Brave/DDG with `union_dedupe_by_url`.
- [ ] Trust & safety filter (hybrid blocklist+curated allowlist, Tranco-backed reputation, always-on SSRF).
- [ ] Defense-in-depth PII redaction at query-egress.

### Phase 6: Adversary (Week 3–4)
- [ ] Adversary agent + `challenge_result` machinery.
- [ ] `adversary_gate` stage as `parallel_map` over tentatively SUPPORTED claims.
- [ ] Cascade `REFUTED` via `mark_dependents_stale`.

### Phase 7: Checkpointing, Replay, Resumability (Week 4)
- [ ] SQLite persistence with PII masking at checkpoint_write.
- [ ] Hash-and-reconstruct replay mode.
- [ ] Session resumption on coordinator restart.

### Phase 8: Structured Replan + Provenance Tree (Week 4–5)
- [ ] `ReplanReason` enum + surgical Planner replan (preserves unchanged evidence).
- [ ] `ProvenanceTree` Pydantic model + edge-typed graph.
- [ ] Postprocessor citation rendering driven by provenance paths.

### Phase 9: Critic + Postprocessor (Week 5)
- [ ] Critic with `iteration_count`, oscillation-aware routing.
- [ ] Postprocessor with markdown/json outputs, configurable citation style, PII pre-synthesis pass.

### Phase 10: Observability (Week 5–6)
- [ ] Trace IDs (`session_id`, `trace_id`, `span_id`) on every A2A envelope.
- [ ] OpenTelemetry spans per stage + per parallel_map item.
- [ ] Prometheus metrics (claim recall, independence, adversary catch-rate, oscillation count, cache hit rate).
- [ ] Cost attribution tags propagated end-to-end.

### Phase 11: Caching + Feedback + A/B (Week 6–7)
- [ ] Search/page/verify/workflow caches (SQLite default, Redis flag).
- [ ] Feedback store keyed on provenance node IDs; weekly offline retraining pipeline.
- [ ] A/B workflow comparison with per-query-class sticky sampling and the weighted composite metric.

---

