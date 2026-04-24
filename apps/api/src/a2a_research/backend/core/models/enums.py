"""Enumeration types for the A2A research system.

All StrEnum classes used across agents, workflow, and UI.
"""

from __future__ import annotations

from enum import StrEnum


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
    """Status of an agent execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(StrEnum):
    """Status of a task in the system."""

    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"


class ReplanReasonCode(StrEnum):
    """Reason codes for replanning decisions."""

    TOO_BROAD = "too_broad"
    TOO_NARROW = "too_narrow"
    MISSING_CLAIM = "missing_claim"
    REDUNDANT_CLAIM = "redundant_claim"
    WRONG_DOMAIN = "wrong_domain"
    AMBIGUOUS_TERM = "ambiguous_term"


class ProvenanceEdgeType(StrEnum):
    """Types of edges in the provenance tree."""

    CLAIM_TO_QUERY = "claim_to_query"
    QUERY_TO_HIT = "query_to_hit"
    HIT_TO_PAGE = "hit_to_page"
    PAGE_TO_PASSAGE = "page_to_passage"
    PASSAGE_TO_VERDICT = "passage_to_verdict"
    PASSAGE_TO_ADVERSARY_CHALLENGE = "passage_to_adversary_challenge"
