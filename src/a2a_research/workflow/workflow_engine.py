"""Claim-centric workflow engine (v2.3).

Implements the full pipeline from workflow.md:
  Preprocess → Clarify → Plan → Claim-centric loop → Synthesize → Critique → Postprocess

The claim-centric loop traverses claims in DAG topological order, gathering evidence
iteratively until all claims are resolved, budget is exhausted, or novelty drops.
"""

from __future__ import annotations

import asyncio
import hashlib
from time import perf_counter
from typing import Any

from a2a.types import TaskState
from pydantic import ValidationError

from a2a_research.a2a import (
    A2AClient,
    extract_data_payload_or_warn,
    get_registry,
)
from a2a_research.app_logging import get_logger
from a2a_research.models import (
    AgentCapability,
    AgentDefinition,
    AgentResult,
    AgentRole,
    AgentStatus,
    BudgetConsumption,
    Claim,
    ClaimDAG,
    ClaimFollowUp,
    ClaimState,
    ClaimVerification,
    EvidenceUnit,
    IndependenceGraph,
    NoveltyTracker,
    ProvenanceEdge,
    ProvenanceEdgeType,
    ProvenanceNode,
    ProvenanceTree,
    ReplanReason,
    ReportOutput,
    ResearchSession,
    Verdict,
    WorkflowBudget,
)
from a2a_research.progress import Bus, ProgressPhase, ProgressQueue, emit
from a2a_research.settings import settings
from a2a_research.tools import PageContent, WebHit

logger = get_logger(__name__)

__all__ = ["run_workflow_v2_async", "run_workflow_v2_sync"]

_AGENT_DEFINITIONS: dict[AgentRole, AgentDefinition] = {
    AgentRole.PREPROCESSOR: AgentDefinition(
        role=AgentRole.PREPROCESSOR,
        capabilities={AgentCapability.PREPROCESS},
        url_env_var="PREPROCESSOR_URL",
    ),
    AgentRole.CLARIFIER: AgentDefinition(
        role=AgentRole.CLARIFIER,
        capabilities={AgentCapability.CLARIFY},
        url_env_var="CLARIFIER_URL",
    ),
    AgentRole.PLANNER: AgentDefinition(
        role=AgentRole.PLANNER,
        capabilities={AgentCapability.DECOMPOSE, AgentCapability.REPLAN},
        url_env_var="PLANNER_URL",
    ),
    AgentRole.SEARCHER: AgentDefinition(
        role=AgentRole.SEARCHER,
        capabilities={AgentCapability.SEARCH},
        url_env_var="SEARCHER_URL",
    ),
    AgentRole.RANKER: AgentDefinition(
        role=AgentRole.RANKER,
        capabilities={AgentCapability.RANK},
        url_env_var="RANKER_URL",
    ),
    AgentRole.READER: AgentDefinition(
        role=AgentRole.READER,
        capabilities={AgentCapability.EXTRACT},
        url_env_var="READER_URL",
    ),
    AgentRole.EVIDENCE_DEDUPLICATOR: AgentDefinition(
        role=AgentRole.EVIDENCE_DEDUPLICATOR,
        capabilities={AgentCapability.NORMALIZE},
        url_env_var="EVIDENCE_DEDUPLICATOR_URL",
    ),
    AgentRole.FACT_CHECKER: AgentDefinition(
        role=AgentRole.FACT_CHECKER,
        capabilities={AgentCapability.VERIFY, AgentCapability.FOLLOW_UP},
        url_env_var="FACT_CHECKER_URL",
    ),
    AgentRole.ADVERSARY: AgentDefinition(
        role=AgentRole.ADVERSARY,
        capabilities={AgentCapability.ADVERSARIAL_VERIFY},
        url_env_var="ADVERSARY_URL",
    ),
    AgentRole.SYNTHESIZER: AgentDefinition(
        role=AgentRole.SYNTHESIZER,
        capabilities={AgentCapability.SYNTHESIZE},
        url_env_var="SYNTHESIZER_URL",
    ),
    AgentRole.CRITIC: AgentDefinition(
        role=AgentRole.CRITIC,
        capabilities={AgentCapability.CRITIQUE},
        url_env_var="CRITIC_URL",
    ),
    AgentRole.POSTPROCESSOR: AgentDefinition(
        role=AgentRole.POSTPROCESSOR,
        capabilities={AgentCapability.POSTPROCESS},
        url_env_var="POSTPROCESSOR_URL",
    ),
}

_STEP_INDEX_V2: dict[AgentRole, int] = {
    AgentRole.PREPROCESSOR: 0,
    AgentRole.CLARIFIER: 1,
    AgentRole.PLANNER: 2,
    AgentRole.SEARCHER: 3,
    AgentRole.RANKER: 4,
    AgentRole.READER: 5,
    AgentRole.EVIDENCE_DEDUPLICATOR: 6,
    AgentRole.FACT_CHECKER: 7,
    AgentRole.ADVERSARY: 8,
    AgentRole.SYNTHESIZER: 9,
    AgentRole.CRITIC: 10,
    AgentRole.POSTPROCESSOR: 11,
}

_TOTAL_STEPS_V2 = len(_STEP_INDEX_V2)


def _budget_from_settings() -> WorkflowBudget:
    wf = settings.workflow
    return WorkflowBudget(
        max_rounds=wf.budget_max_rounds,
        max_tokens=wf.budget_max_tokens,
        max_wall_seconds=float(wf.budget_max_wall_seconds),
        max_http_calls=50,
        max_urls_fetched=20,
        min_marginal_evidence=wf.budget_min_marginal_evidence,
        max_critic_revision_loops=wf.budget_max_critic_revision_loops,
    )


_PER_STAGE_TIMEOUTS: dict[AgentRole, float] = {
    AgentRole.PREPROCESSOR: 10.0,
    AgentRole.CLARIFIER: 15.0,
    AgentRole.PLANNER: 20.0,
    AgentRole.SEARCHER: 15.0,
    AgentRole.RANKER: 10.0,
    AgentRole.READER: 30.0,
    AgentRole.EVIDENCE_DEDUPLICATOR: 10.0,
    AgentRole.FACT_CHECKER: 45.0,
    AgentRole.ADVERSARY: 30.0,
    AgentRole.SYNTHESIZER: 60.0,
    AgentRole.CRITIC: 30.0,
    AgentRole.POSTPROCESSOR: 10.0,
}


def _stage_timeout(role: AgentRole) -> float:
    return _PER_STAGE_TIMEOUTS.get(role, 30.0)


async def run_workflow_v2_async(
    query: str, progress_queue: ProgressQueue | None = None
) -> ResearchSession:
    session = ResearchSession(query=query)
    session.roles = list(_STEP_INDEX_V2.keys())
    session.ensure_agent_results()
    started = perf_counter()
    logger.info("workflow_v2 start session_id=%s query=%r", session.id, query)

    client = A2AClient(get_registry())
    if progress_queue is not None:
        Bus.register(session.id, progress_queue)

    budget = _budget_from_settings()
    session.budget_consumed = BudgetConsumption()

    try:
        await asyncio.wait_for(
            _drive_v2(session, client, query, budget),
            timeout=settings.workflow_timeout,
        )
    except TimeoutError:
        session.error = f"Workflow timed out after {settings.workflow_timeout:.0f}s — partial results below."
        _mark_running_failed(session)
        logger.warning("workflow_v2 timed out session_id=%s", session.id)
    except Exception as exc:
        session.error = str(exc)
        _mark_running_failed(session)
        logger.exception("workflow_v2 failed session_id=%s", session.id)

    elapsed_ms = (perf_counter() - started) * 1000
    logger.info(
        "workflow_v2 done session_id=%s elapsed_ms=%.1f error=%s",
        session.id,
        elapsed_ms,
        session.error,
    )
    if progress_queue is not None:
        progress_queue.put_nowait(None)
        Bus.unregister(session.id)
    return session


def run_workflow_v2_sync(query: str) -> ResearchSession:
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        msg = (
            "run_workflow_v2_sync cannot be called from a running event loop; "
            "use run_workflow_v2_async instead."
        )
        raise RuntimeError(msg)
    return asyncio.run(run_workflow_v2_async(query))


async def _drive_v2(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
) -> None:
    """Main v2 workflow driver."""

    workflow_start = perf_counter()

    def _update_wall_seconds() -> None:
        session.budget_consumed.wall_seconds = perf_counter() - workflow_start

    def _emit_budget(
        session_id: str, role: AgentRole | None, label: str
    ) -> None:
        _update_wall_seconds()
        bc = session.budget_consumed
        detail = (
            f"rounds={bc.rounds}/{budget.max_rounds} "
            f"tokens={bc.tokens_consumed}/{budget.max_tokens} "
            f"wall_s={bc.wall_seconds:.1f}/{budget.max_wall_seconds:.0f} "
            f"http={bc.http_calls}/{budget.max_http_calls} "
            f"urls={bc.urls_fetched} "
            f"critic_loops={bc.critic_revision_loops}/{budget.max_critic_revision_loops}"
        )
        _emit_v2(
            session_id, role, ProgressPhase.STEP_SUBSTEP, label, detail=detail
        )

    # ─── Preprocess ───────────────────────────────────────────────────────────
    preprocess_result = await _run_agent(
        session,
        client,
        AgentRole.PREPROCESSOR,
        {"query": query, "session_id": session.id},
    )
    _update_wall_seconds()
    if _should_abort_preprocessing(preprocess_result):
        session.error = "Query classified as unanswerable or sensitive."
        _set_status(
            session,
            AgentRole.PREPROCESSOR,
            AgentStatus.COMPLETED,
            "Aborted query.",
        )
        session.final_report = _abort_report(query, session.error)
        return

    sanitized_query = preprocess_result.get("sanitized_query", query)
    query_class = preprocess_result.get(
        "query_class",
        preprocess_result.get("class", "factual"),
    )
    domain_hints = preprocess_result.get("domain_hints", [])

    # ─── Clarify ──────────────────────────────────────────────────────────────
    clarify_result = await _run_agent(
        session,
        client,
        AgentRole.CLARIFIER,
        {
            "query": sanitized_query,
            "query_class": query_class,
            "session_id": session.id,
        },
    )
    _update_wall_seconds()
    committed_interpretation = clarify_result.get(
        "committed_interpretation", sanitized_query
    )

    # ─── Plan ─────────────────────────────────────────────────────────────────
    _emit_v2(
        session.id,
        AgentRole.PLANNER,
        ProgressPhase.STEP_STARTED,
        "planner_started",
    )
    _set_status(
        session, AgentRole.PLANNER, AgentStatus.RUNNING, "Decomposing query…"
    )
    plan_result = await _run_agent(
        session,
        client,
        AgentRole.PLANNER,
        {
            "query": committed_interpretation,
            "domain_hints": domain_hints,
            "session_id": session.id,
        },
    )
    _update_wall_seconds()
    claims = _coerce_claims(plan_result.get("claims", []))
    dag = _coerce_dag(plan_result.get("claim_dag", {}), claims=claims)
    seed_queries = [
        str(q)
        for q in plan_result.get("seed_queries", [])
        if isinstance(q, str)
    ]

    if not claims:
        _set_status(
            session,
            AgentRole.PLANNER,
            AgentStatus.FAILED,
            "No claims produced.",
        )
        session.error = "Planner failed to decompose query."
        session.final_report = _planner_failed_report(query)
        return

    _set_status(
        session,
        AgentRole.PLANNER,
        AgentStatus.COMPLETED,
        f"Extracted {len(claims)} claim(s), DAG: {len(dag.nodes)} nodes, {len(dag.edges)} edges.",
    )
    _emit_v2(
        session.id,
        AgentRole.PLANNER,
        ProgressPhase.STEP_COMPLETED,
        "planner_completed",
    )

    # Initialize claim state
    claim_state = ClaimState(
        original_claims=claims,
        dag=dag,
        verification={},
        unresolved_claim_ids=[c.id for c in claims],
        stale_claim_ids=[],
        resolved_claim_ids=[],
    )
    for c in claims:
        claim_state.verification[c.id] = ClaimVerification(claim_id=c.id)
    claim_state.refresh_resolution_lists()
    session.claim_state = claim_state

    # ─── Claim-centric evidence loop ──────────────────────────────────────────
    accumulated_evidence: list[EvidenceUnit] = []
    independence_graph = IndependenceGraph()
    provenance_tree = ProvenanceTree()
    novelty_tracker = NoveltyTracker()
    loop_round = 0
    previous_round_marginal_gain: int | None = None

    claim_queries = list(dict.fromkeys(seed_queries))

    while True:
        loop_round += 1
        session.budget_consumed.rounds = loop_round
        _update_wall_seconds()

        # Reset novelty tracker at start of each round
        novelty_tracker = NoveltyTracker()
        session.novelty_tracker = novelty_tracker

        if claim_state.all_resolved:
            logger.info("All claims resolved after %s rounds", loop_round)
            break
        if session.budget_consumed.is_exhausted(budget):
            logger.info("Budget exhausted after %s rounds", loop_round)
            _emit_budget(session.id, None, "budget_exhausted")
            break
        if (
            previous_round_marginal_gain is not None
            and previous_round_marginal_gain < budget.min_marginal_evidence
        ):
            logger.info("Novelty below threshold after %s rounds", loop_round)
            break

        to_process = _claims_to_process(claim_state)
        if not to_process:
            logger.info("No claims to process in round %s", loop_round)
            break

        _emit_budget(
            session.id, AgentRole.SEARCHER, f"round_{loop_round}_start"
        )

        _emit_v2(
            session.id,
            AgentRole.SEARCHER,
            ProgressPhase.STEP_STARTED,
            f"evidence_gathering_round_{loop_round}",
            detail=f"claims={len(to_process)}",
        )

        # ─── Search ─────────────────────────────────────────────────────────
        search_result = await _run_agent(
            session,
            client,
            AgentRole.SEARCHER,
            {
                "queries": claim_queries,
                "freshness_hints": claim_state.freshness_windows,
                "session_id": session.id,
            },
        )
        raw_hits = search_result.get("hits", [])
        hits = [_coerce_web_hit(h) for h in raw_hits]
        hits = [h for h in hits if h is not None]
        _update_wall_seconds()

        if not hits:
            logger.warning("No search hits in round %s", loop_round)
            break

        if session.budget_consumed.is_exhausted(budget):
            logger.info(
                "Budget exhausted after search in round %s", loop_round
            )
            _emit_budget(
                session.id, AgentRole.SEARCHER, "budget_exhausted_after_search"
            )
            break

        # ─── Rank ───────────────────────────────────────────────────────────
        rank_result = await _run_agent(
            session,
            client,
            AgentRole.RANKER,
            {
                "hits": [h.model_dump(mode="json") for h in hits],
                "unresolved_claims": [
                    c.model_dump(mode="json") for c in to_process
                ],
                "freshness_windows": {
                    k: v.model_dump(mode="json")
                    for k, v in claim_state.freshness_windows.items()
                },
                "session_id": session.id,
            },
        )
        ranked_urls = [str(u) for u in rank_result.get("ranked_urls", [])]
        fetch_budget = min(
            budget.max_urls_fetched - session.budget_consumed.urls_fetched, 8
        )
        urls_to_fetch = ranked_urls[:fetch_budget]
        _update_wall_seconds()

        if not urls_to_fetch:
            logger.warning(
                "No URLs to fetch after ranking in round %s", loop_round
            )
            break

        # ─── Read ───────────────────────────────────────────────────────────
        read_result = await _run_agent(
            session,
            client,
            AgentRole.READER,
            {
                "urls": urls_to_fetch,
                "claims": [c.model_dump(mode="json") for c in to_process],
                "session_id": session.id,
            },
        )
        raw_pages = read_result.get("pages", [])
        pages = [_coerce_page_content(p) for p in raw_pages]
        pages = [
            p for p in pages if p is not None and not p.error and p.markdown
        ]
        session.budget_consumed.urls_fetched += len(urls_to_fetch)
        _update_wall_seconds()

        if not pages:
            logger.warning("No pages extracted in round %s", loop_round)
            break

        if session.budget_consumed.is_exhausted(budget):
            logger.info("Budget exhausted after read in round %s", loop_round)
            _emit_budget(
                session.id, AgentRole.READER, "budget_exhausted_after_read"
            )
            break

        # ─── Normalize / Deduplicate ────────────────────────────────────────
        normalize_result = await _run_agent(
            session,
            client,
            AgentRole.EVIDENCE_DEDUPLICATOR,
            {
                "pages": [p.model_dump(mode="json") for p in pages],
                "existing_evidence": [
                    e.model_dump(mode="json") for e in accumulated_evidence
                ],
                "session_id": session.id,
            },
        )
        raw_evidence = normalize_result.get("new_evidence", [])
        new_evidence = [_coerce_evidence_unit(e) for e in raw_evidence]
        new_evidence = [e for e in new_evidence if e is not None]

        # Track novelty for this round
        novelty_tracker.new_unique_hits += len(hits)
        novelty_tracker.new_unique_pages += len(pages)
        novelty_tracker.new_supporting_evidence_spans += sum(
            len(e.quoted_passages) for e in new_evidence
        )

        # Track new independent publishers
        seen_publishers = {
            ev.publisher_id for ev in accumulated_evidence if ev.publisher_id
        }
        new_publishers = {
            ev.publisher_id
            for ev in new_evidence
            if ev.publisher_id and ev.publisher_id not in seen_publishers
        }
        novelty_tracker.new_independent_publishers = len(new_publishers)
        session.novelty_tracker = novelty_tracker

        # Merge evidence
        existing_ids = {e.id for e in accumulated_evidence}
        deduped_new = [e for e in new_evidence if e.id not in existing_ids]
        accumulated_evidence.extend(deduped_new)
        independence_graph.update(deduped_new)
        session.accumulated_evidence = accumulated_evidence
        session.independence_graph = independence_graph

        # Update provenance
        for claim in to_process:
            claim_node_id = _claim_node_id(claim.id)
            _ensure_provenance_node(
                provenance_tree,
                ProvenanceNode(
                    id=claim_node_id, node_type="claim", ref_id=claim.id
                ),
            )
        for hit in hits:
            hit_node_id = _hit_node_id(hit.url)
            _ensure_provenance_node(
                provenance_tree,
                ProvenanceNode(
                    id=hit_node_id,
                    node_type="hit",
                    ref_id=hit.url,
                    metadata={
                        "title": hit.title,
                        "source": hit.source,
                        "score": hit.score,
                    },
                ),
            )
        for claim in to_process:
            claim_node_id = _claim_node_id(claim.id)
            for query_text in claim_queries:
                query_node_id = _query_node_id(claim.id, query_text)
                _ensure_provenance_node(
                    provenance_tree,
                    ProvenanceNode(
                        id=query_node_id,
                        node_type="query",
                        ref_id=query_text,
                        metadata={"claim_id": claim.id},
                    ),
                )
                _ensure_provenance_edge(
                    provenance_tree,
                    claim_node_id,
                    query_node_id,
                    ProvenanceEdgeType.CLAIM_TO_QUERY,
                )
                for hit in hits:
                    _ensure_provenance_edge(
                        provenance_tree,
                        query_node_id,
                        _hit_node_id(hit.url),
                        ProvenanceEdgeType.QUERY_TO_HIT,
                    )
        for ev in deduped_new:
            page_node_id = _page_node_id(ev.id)
            _ensure_provenance_node(
                provenance_tree,
                ProvenanceNode(
                    id=page_node_id,
                    node_type="page",
                    ref_id=ev.id,
                    metadata={"url": ev.url, "title": ev.title},
                ),
            )
            _ensure_provenance_edge(
                provenance_tree,
                _hit_node_id(ev.url),
                page_node_id,
                ProvenanceEdgeType.HIT_TO_PAGE,
            )
            for passage in ev.quoted_passages:
                passage_node_id = _passage_node_id(passage.id)
                _ensure_provenance_node(
                    provenance_tree,
                    ProvenanceNode(
                        id=passage_node_id,
                        node_type="passage",
                        ref_id=passage.id,
                        metadata={"evidence_id": ev.id},
                    ),
                )
                _ensure_provenance_edge(
                    provenance_tree,
                    page_node_id,
                    passage_node_id,
                    ProvenanceEdgeType.PAGE_TO_PASSAGE,
                )
        session.provenance_tree = provenance_tree

        _update_wall_seconds()
        if session.budget_consumed.is_exhausted(budget):
            logger.info(
                "Budget exhausted after normalize in round %s", loop_round
            )
            _emit_budget(
                session.id,
                AgentRole.EVIDENCE_DEDUPLICATOR,
                "budget_exhausted_after_normalize",
            )
            break

        # ─── Verify ─────────────────────────────────────────────────────────
        replan_reasons: list[ReplanReason] = []
        if deduped_new:
            verify_result = await _run_agent(
                session,
                client,
                AgentRole.FACT_CHECKER,
                {
                    "query": query,
                    "claims": [c.model_dump(mode="json") for c in to_process],
                    "claim_dag": claim_state.dag.model_dump(mode="json"),
                    "evidence": [p.model_dump(mode="json") for p in pages],
                    "new_evidence": [
                        e.model_dump(mode="json") for e in deduped_new
                    ],
                    "accumulated_evidence": [
                        e.model_dump(mode="json") for e in accumulated_evidence
                    ],
                    "independence_graph": independence_graph.model_dump(
                        mode="json"
                    ),
                    "session_id": session.id,
                },
            )
            updated_state = _coerce_claim_state(
                verify_result.get("updated_claim_state", {}),
                fallback_claims=claim_state.original_claims,
                fallback_dag=claim_state.dag,
            )
            if updated_state:
                claim_state = updated_state
            else:
                claim_state = _merge_verified_claims_into_state(
                    claim_state,
                    _coerce_claims(verify_result.get("verified_claims", [])),
                    independence_graph,
                )
            claim_state.refresh_resolution_lists()
            session.claim_state = claim_state

            follow_ups = _coerce_follow_ups(
                verify_result.get("claim_follow_ups", [])
            )
            replan_reasons = _coerce_replan_reasons(
                verify_result.get("replan_reasons", [])
            )
            session.replan_reasons = replan_reasons

            claim_queries = []
            for fu in follow_ups:
                claim_queries.extend(fu.queries)
            claim_queries = list(dict.fromkeys(claim_queries))

            for verification in claim_state.verification.values():
                verdict_node_id = _verdict_node_id(verification.claim_id)
                _ensure_provenance_node(
                    provenance_tree,
                    ProvenanceNode(
                        id=verdict_node_id,
                        node_type="verdict",
                        ref_id=verification.claim_id,
                        metadata={
                            "verdict": verification.verdict.value,
                            "confidence": verification.confidence,
                        },
                    ),
                )
                claim = claim_state.get_claim(verification.claim_id)
                if claim is not None:
                    _ensure_provenance_edge(
                        provenance_tree,
                        _claim_node_id(claim.id),
                        verdict_node_id,
                        ProvenanceEdgeType.PASSAGE_TO_VERDICT,
                    )

            _update_wall_seconds()
            if session.budget_consumed.is_exhausted(budget):
                logger.info(
                    "Budget exhausted after verify in round %s", loop_round
                )
                _emit_budget(
                    session.id,
                    AgentRole.FACT_CHECKER,
                    "budget_exhausted_after_verify",
                )
                break

            # ─── Adversary gate ───────────────────────────────────────────
            tentative = claim_state.tentatively_supported_claim_ids
            if tentative:
                adversary_result = await _run_agent(
                    session,
                    client,
                    AgentRole.ADVERSARY,
                    {
                        "claims": [
                            c.model_dump(mode="json")
                            for c in claim_state.original_claims
                            if c.id in tentative
                        ],
                        "evidence": [
                            e.model_dump(mode="json")
                            for e in accumulated_evidence
                        ],
                        "session_id": session.id,
                    },
                )
                challenges = adversary_result.get("challenge_results", [])
                for ch in challenges:
                    claim_id = ch.get("claim_id")
                    result = ch.get("challenge_result", "HOLDS")
                    v = claim_state.verification.get(claim_id)
                    if v is not None:
                        v.adversary_result = result
                        if result == "REFUTED":
                            v.verdict = Verdict.REFUTED
                            claim_state.mark_dependents_stale(claim_id)
                        elif result == "WEAKENED":
                            v.verdict = Verdict.MIXED
                        _ensure_provenance_node(
                            provenance_tree,
                            ProvenanceNode(
                                id=_challenge_node_id(claim_id),
                                node_type="challenge",
                                ref_id=str(claim_id),
                                metadata={"challenge_result": result},
                            ),
                        )
                        _ensure_provenance_edge(
                            provenance_tree,
                            _verdict_node_id(str(claim_id)),
                            _challenge_node_id(str(claim_id)),
                            ProvenanceEdgeType.PASSAGE_TO_ADVERSARY_CHALLENGE,
                        )
                claim_state.refresh_resolution_lists()
                session.claim_state = claim_state

                _update_wall_seconds()
                if session.budget_consumed.is_exhausted(budget):
                    logger.info(
                        "Budget exhausted after adversary in round %s",
                        loop_round,
                    )
                    _emit_budget(
                        session.id,
                        AgentRole.ADVERSARY,
                        "budget_exhausted_after_adversary",
                    )
                    break

        # ─── Snapshot ───────────────────────────────────────────────────────
        snapshot_result = await _run_agent(
            session,
            client,
            AgentRole.SYNTHESIZER,
            {
                "query": query,
                "claim_state": claim_state.model_dump(mode="json"),
                "evidence": [
                    e.model_dump(mode="json") for e in accumulated_evidence
                ],
                "mode": "tentative",
                "session_id": session.id,
            },
        )
        snapshot_report = _coerce_report(snapshot_result.get("report"))
        if snapshot_report:
            session.tentative_report = snapshot_report
        _update_wall_seconds()

        if session.budget_consumed.is_exhausted(budget):
            logger.info(
                "Budget exhausted after snapshot in round %s", loop_round
            )
            _emit_budget(
                session.id,
                AgentRole.SYNTHESIZER,
                "budget_exhausted_after_snapshot",
            )
            break

        # ─── Replan check ───────────────────────────────────────────────────
        if replan_reasons and loop_round < budget.max_rounds:
            replan_result = await _run_agent(
                session,
                client,
                AgentRole.PLANNER,
                {
                    "original_query": query,
                    "current_claims": [
                        c.model_dump(mode="json")
                        for c in claim_state.original_claims
                    ],
                    "current_dag": claim_state.dag.model_dump(mode="json"),
                    "replan_reasons": [
                        r.model_dump(mode="json") for r in replan_reasons
                    ],
                    "mode": "surgical",
                    "session_id": session.id,
                },
            )
            revised_claims = _coerce_claims(
                replan_result.get(
                    "revised_claims", replan_result.get("claims", [])
                )
            )
            revised_dag = _coerce_dag(
                replan_result.get(
                    "revised_dag", replan_result.get("claim_dag", {})
                ),
                claims=revised_claims,
            )
            if revised_claims:
                claim_state.original_claims = revised_claims
                claim_state.dag = revised_dag
                for c in revised_claims:
                    if c.id not in claim_state.verification:
                        claim_state.verification[c.id] = ClaimVerification(
                            claim_id=c.id
                        )
                claim_state.refresh_resolution_lists()
                session.claim_state = claim_state
                claim_queries = [
                    str(q)
                    for q in replan_result.get(
                        "replan_queries", replan_result.get("seed_queries", [])
                    )
                    if isinstance(q, str)
                ]
            _update_wall_seconds()

        # Deduplicated follow-ups termination
        deduplicated_follow_ups = (
            list(dict.fromkeys(claim_queries)) if claim_queries else []
        )
        if not deduplicated_follow_ups and claim_state.all_resolved:
            break
        if not deduplicated_follow_ups and not claim_state.all_resolved:
            logger.info(
                "No follow-up queries remaining in round %s", loop_round
            )
            break

        previous_round_marginal_gain = novelty_tracker.marginal_gain
        _emit_budget(session.id, None, f"round_{loop_round}_end")

    # ─── Final Synthesize ─────────────────────────────────────────────────────
    _emit_v2(
        session.id,
        AgentRole.SYNTHESIZER,
        ProgressPhase.STEP_STARTED,
        "synthesizer_started",
    )
    _set_status(
        session, AgentRole.SYNTHESIZER, AgentStatus.RUNNING, "Writing report…"
    )
    syn_result = await _run_agent(
        session,
        client,
        AgentRole.SYNTHESIZER,
        {
            "query": query,
            "claim_state": claim_state.model_dump(mode="json")
            if claim_state
            else {},
            "evidence": [
                e.model_dump(mode="json") for e in accumulated_evidence
            ],
            "provenance_tree": provenance_tree.model_dump(mode="json"),
            "tentative_report": session.tentative_report.model_dump(
                mode="json"
            )
            if session.tentative_report
            else None,
            "session_id": session.id,
        },
    )
    _update_wall_seconds()
    report = _coerce_report(syn_result.get("report"))
    session.report = report
    session.final_report = report.to_markdown() if report else ""
    _set_status(
        session,
        AgentRole.SYNTHESIZER,
        AgentStatus.COMPLETED if report else AgentStatus.FAILED,
        "Report synthesized." if report else "Failed to synthesize report.",
    )
    _emit_v2(
        session.id,
        AgentRole.SYNTHESIZER,
        ProgressPhase.STEP_COMPLETED if report else ProgressPhase.STEP_FAILED,
        "synthesizer_completed" if report else "synthesizer_failed",
    )

    # ─── Critique ─────────────────────────────────────────────────────────────
    critique_passed = True
    if report:
        crit_result = await _run_agent(
            session,
            client,
            AgentRole.CRITIC,
            {
                "report": report.model_dump(mode="json"),
                "claim_state": claim_state.model_dump(mode="json")
                if claim_state
                else {},
                "evidence": [
                    e.model_dump(mode="json") for e in accumulated_evidence
                ],
                "session_id": session.id,
            },
        )
        _update_wall_seconds()
        critique_passed = bool(crit_result.get("passed", True))
        session.critique = crit_result.get("critique", "")
        iteration_count = int(crit_result.get("iteration_count", 0))

        if (
            not critique_passed
            and iteration_count < budget.max_critic_revision_loops
        ):
            session.budget_consumed.critic_revision_loops += 1
            logger.info(
                "Critic suggests revision (iteration %s)", iteration_count
            )

    # ─── Postprocess ──────────────────────────────────────────────────────────
    post_result = await _run_agent(
        session,
        client,
        AgentRole.POSTPROCESSOR,
        {
            "report": report.model_dump(mode="json") if report else {},
            "claim_state": claim_state.model_dump(mode="json")
            if claim_state
            else {},
            "provenance_tree": provenance_tree.model_dump(mode="json"),
            "output_formats": ["markdown", "json"],
            "citation_style": "hyperlinked_footnotes",
            "warnings": [] if critique_passed else [session.critique],
            "session_id": session.id,
        },
    )
    _update_wall_seconds()
    session.formatted_outputs = post_result.get("formatted_outputs", {})
    if session.formatted_outputs.get("markdown"):
        session.final_report = session.formatted_outputs["markdown"]

    _emit_budget(session.id, None, "workflow_final_budget")
    _emit_v2(
        session.id, None, ProgressPhase.STEP_COMPLETED, "workflow_completed"
    )


# ─── Agent call helper ──────────────────────────────────────────────────────────


async def _run_agent(
    session: ResearchSession,
    client: A2AClient,
    role: AgentRole,
    payload: dict[str, Any],
    *,
    agent_timeout: float | None = None,
) -> dict[str, Any]:
    """Call an agent via A2A and return its payload.

    If the agent is not registered (new agents not yet deployed),
    returns a passthrough result so the workflow can degrade gracefully.
    """
    stage_timeout = (
        agent_timeout if agent_timeout is not None else _stage_timeout(role)
    )
    definition = _AGENT_DEFINITIONS.get(role)
    if definition is None:
        return dict(payload)

    _set_status(session, role, AgentStatus.RUNNING, f"Calling {role.value}…")

    try:
        task = await asyncio.wait_for(
            client.send(role, payload=payload, from_role=AgentRole.PLANNER),
            timeout=stage_timeout,
        )
        session.budget_consumed.http_calls += 1
    except TimeoutError:
        logger.warning(
            "Agent %s timed out after %.1fs", role.value, stage_timeout
        )
        _set_status(
            session,
            role,
            AgentStatus.FAILED,
            f"Timeout after {stage_timeout:.0f}s.",
        )
        return {}
    except Exception as exc:
        logger.warning("Agent %s unreachable: %s", role.value, exc)
        _set_status(session, role, AgentStatus.FAILED, f"Unreachable: {exc}")
        return {}

    if _task_failed(task):
        _set_status(
            session, role, AgentStatus.FAILED, "Agent reported failure."
        )
        return {}

    data = _payload(task)
    _set_status(session, role, AgentStatus.COMPLETED, "Done.")
    return data


# ─── Claim processing helpers ───────────────────────────────────────────────────


def _claims_to_process(claim_state: ClaimState) -> list[Claim]:
    """Unresolved + STALE claims, sorted by DAG topological order."""
    order = claim_state.dag.topological_order()
    if not order:
        order = [c.id for c in claim_state.original_claims]
    queue = []
    for claim_id in order:
        v = claim_state.verification.get(claim_id)
        if v is None:
            continue
        if v.verdict not in (Verdict.UNRESOLVED, Verdict.STALE):
            continue
        parents = claim_state.dag.parents_of(claim_id)
        if any(
            claim_state.verification.get(p)
            and claim_state.verification[p].verdict == Verdict.REFUTED
            for p in parents
        ):
            v.verdict = Verdict.STALE
            continue
        claim = next(
            (c for c in claim_state.original_claims if c.id == claim_id), None
        )
        if claim:
            queue.append(claim)
    return queue


def _should_abort_preprocessing(result: dict[str, Any]) -> bool:
    query_class = result.get("query_class", "")
    confidence = float(
        result.get(
            "query_class_confidence", result.get("class_confidence", 0.0)
        )
    )
    return query_class == "unanswerable" and confidence > 0.8


# ─── Status / event helpers ─────────────────────────────────────────────────────


def _set_status(
    session: ResearchSession,
    role: AgentRole,
    status: AgentStatus,
    message: str,
) -> None:
    session.agent_results[role] = AgentResult(
        role=role, status=status, message=message
    )


def _emit_v2(
    session_id: str,
    role: AgentRole | None,
    phase: ProgressPhase,
    label: str,
    detail: str = "",
) -> None:
    step_index = _STEP_INDEX_V2.get(role, 0) if role else 0
    emit(
        session_id,
        phase,
        role,
        step_index,
        _TOTAL_STEPS_V2,
        label,
        detail=detail,
    )


def _mark_running_failed(session: ResearchSession) -> None:
    for role, result in list(session.agent_results.items()):
        if result.status == AgentStatus.RUNNING:
            session.agent_results[role] = result.model_copy(
                update={"status": AgentStatus.FAILED, "message": "Aborted."}
            )


# ─── Coercion helpers ───────────────────────────────────────────────────────────


def _payload(task: Any) -> dict[str, Any]:
    if task is None:
        return {}
    return extract_data_payload_or_warn(task)


def _task_failed(task: Any) -> bool:
    status = getattr(task, "status", None)
    state = getattr(status, "state", None)
    return state == TaskState.TASK_STATE_FAILED


def _coerce_claims(raw: Any) -> list[Claim]:
    claims: list[Claim] = []
    for item in raw or []:
        if isinstance(item, Claim):
            claims.append(item)
            continue
        if isinstance(item, dict):
            try:
                claims.append(Claim.model_validate(item))
            except ValidationError:
                continue
    return claims


def _coerce_dag(raw: Any, *, claims: list[Claim] | None = None) -> ClaimDAG:
    if isinstance(raw, ClaimDAG):
        dag = raw
    elif isinstance(raw, dict):
        try:
            dag = ClaimDAG.model_validate(raw)
        except ValidationError:
            dag = ClaimDAG()
    else:
        dag = ClaimDAG()
    if not dag.nodes and claims:
        dag.nodes = [claim.id for claim in claims]
    elif claims:
        known = set(dag.nodes)
        for claim in claims:
            if claim.id not in known:
                dag.nodes.append(claim.id)
                known.add(claim.id)
    return dag


def _coerce_claim_state(
    raw: Any,
    *,
    fallback_claims: list[Claim] | None = None,
    fallback_dag: ClaimDAG | None = None,
) -> ClaimState | None:
    if isinstance(raw, ClaimState):
        state = raw
    elif isinstance(raw, dict):
        try:
            state = ClaimState.model_validate(raw)
        except ValidationError:
            state = None
    else:
        state = None
    if state is None:
        return None
    if fallback_claims and not state.original_claims:
        state.original_claims = fallback_claims
    if fallback_dag and not state.dag.nodes and not state.dag.edges:
        state.dag = fallback_dag
    state.refresh_resolution_lists()
    return state


def _coerce_follow_ups(raw: Any) -> list[ClaimFollowUp]:
    result: list[ClaimFollowUp] = []
    for item in raw or []:
        if isinstance(item, ClaimFollowUp):
            result.append(item)
            continue
        if isinstance(item, dict):
            try:
                result.append(ClaimFollowUp.model_validate(item))
            except ValidationError:
                continue
    return result


def _coerce_replan_reasons(raw: Any) -> list[ReplanReason]:
    result: list[ReplanReason] = []
    for item in raw or []:
        if isinstance(item, ReplanReason):
            result.append(item)
            continue
        if isinstance(item, dict):
            try:
                result.append(ReplanReason.model_validate(item))
            except ValidationError:
                continue
    return result


def _coerce_evidence_unit(raw: Any) -> EvidenceUnit | None:
    if isinstance(raw, EvidenceUnit):
        return raw
    if isinstance(raw, dict):
        try:
            return EvidenceUnit.model_validate(raw)
        except ValidationError:
            pass
    return None


def _coerce_web_hit(raw: Any) -> WebHit | None:
    if isinstance(raw, WebHit):
        return raw
    if isinstance(raw, dict):
        try:
            return WebHit.model_validate(raw)
        except ValidationError:
            pass
    return None


def _coerce_page_content(raw: Any) -> PageContent | None:
    if isinstance(raw, PageContent):
        return raw
    if isinstance(raw, dict):
        try:
            return PageContent.model_validate(raw)
        except ValidationError:
            pass
    return None


def _coerce_report(raw: Any) -> ReportOutput | None:
    if isinstance(raw, ReportOutput):
        return raw
    if isinstance(raw, dict):
        try:
            return ReportOutput.model_validate(raw)
        except ValidationError:
            pass
    return None


def _merge_verified_claims_into_state(
    claim_state: ClaimState,
    verified_claims: list[Claim],
    independence_graph: IndependenceGraph,
) -> ClaimState:
    if not verified_claims:
        return claim_state
    for verified in verified_claims:
        verification = claim_state.verification.get(verified.id)
        if verification is None:
            verification = ClaimVerification(claim_id=verified.id)
            claim_state.verification[verified.id] = verification
        verification.verdict = verified.verdict
        verification.confidence = verified.confidence
        verification.independent_source_count = (
            independence_graph.independent_source_count(verified.id)
        )
        verification.supporting_evidence_ids = list(verified.sources)
        if verified.verdict == Verdict.REFUTED:
            claim_state.mark_dependents_stale(verified.id)
    claim_state.refresh_resolution_lists()
    return claim_state


def _ensure_provenance_node(
    tree: ProvenanceTree, node: ProvenanceNode
) -> None:
    if node.id not in tree.nodes:
        tree.add_node(node)


def _ensure_provenance_edge(
    tree: ProvenanceTree,
    src: str,
    dst: str,
    edge_type: ProvenanceEdgeType,
) -> None:
    exists = any(
        edge.src == src and edge.dst == dst and edge.edge_type == edge_type
        for edge in tree.edges
    )
    if not exists:
        tree.add_edge(ProvenanceEdge(src=src, dst=dst, edge_type=edge_type))


def _claim_node_id(claim_id: str) -> str:
    return f"claim::{claim_id}"


def _query_node_id(claim_id: str, query_text: str) -> str:
    digest = hashlib.sha1(query_text.encode("utf-8")).hexdigest()[:12]
    return f"query::{claim_id}::{digest}"


def _hit_node_id(url: str) -> str:
    return f"hit::{url}"


def _page_node_id(evidence_id: str) -> str:
    return f"page::{evidence_id}"


def _passage_node_id(passage_id: str) -> str:
    return f"passage::{passage_id}"


def _verdict_node_id(claim_id: str) -> str:
    return f"verdict::{claim_id}"


def _challenge_node_id(claim_id: str) -> str:
    return f"challenge::{claim_id}"


# ─── Report helpers ─────────────────────────────────────────────────────────────


def _planner_failed_report(query: str) -> str:
    return "\n".join(
        [
            "# Planner failed",
            "",
            f"**Query:** {query}",
            "",
            "The planner could not decompose this query into claims, so the pipeline stopped.",
            "",
        ]
    )


def _abort_report(query: str, reason: str) -> str:
    return "\n".join(
        [
            "# Research unavailable",
            "",
            f"**Query:** {query}",
            "",
            reason,
            "",
        ]
    )
