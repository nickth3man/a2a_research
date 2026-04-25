"""Agent card specification data."""

from __future__ import annotations

from core.models.enums import AgentRole

CARD_SPECS: dict[AgentRole, dict[str, str | list[str]]] = {
    AgentRole.PLANNER: {
        "name": "Planner",
        "description": (
            "Decomposes a research query into atomic claims and seed"
            " search queries."
        ),
        "skill_id": "query-decomposition",
        "skill_description": (
            "Break a user question into 3-6 atomic verifiable claims."
        ),
        "tags": ["planning", "decomposition"],
    },
    AgentRole.SEARCHER: {
        "name": "Searcher",
        "description": (
            "Runs web search refinement loops and returns ranked URLs."
        ),
        "skill_id": "web-search",
        "skill_description": (
            "Concurrent web search with merged, deduplicated results."
        ),
        "tags": ["search", "retrieval"],
    },
    AgentRole.READER: {
        "name": "Reader",
        "description": "Fetches URLs and extracts the main text as markdown.",
        "skill_id": "page-extraction",
        "skill_description": (
            "Main-content extraction via trafilatura for one or many URLs."
        ),
        "tags": ["extraction", "reading"],
    },
    AgentRole.FACT_CHECKER: {
        "name": "FactChecker",
        "description": (
            "Coordinates Searcher and Reader in a bounded loop to"
            " verify atomic claims against web evidence until they"
            " converge."
        ),
        "skill_id": "claim-verification",
        "skill_description": "Iterative verification loop over web evidence.",
        "tags": ["verification", "loop", "coordination"],
    },
    AgentRole.SYNTHESIZER: {
        "name": "Synthesizer",
        "description": (
            "Turns verified claims and cited sources into a structured"
            " markdown report."
        ),
        "skill_id": "report-synthesis",
        "skill_description": (
            "Structured Pydantic output → markdown report with citations."
        ),
        "tags": ["synthesis", "writing"],
    },
    AgentRole.CLARIFIER: {
        "name": "Clarifier",
        "description": "Disambiguates underspecified queries.",
        "skill_id": "query-clarification",
        "skill_description": (
            "Breaks ambiguous user questions into precise, actionable queries."
        ),
        "tags": ["clarification", "disambiguation"],
    },
    AgentRole.PREPROCESSOR: {
        "name": "Preprocessor",
        "description": "Classifies, sanitizes, and scans queries for PII.",
        "skill_id": "preprocess",
        "skill_description": "Classify query type, sanitize, and detect PII.",
        "tags": ["preprocess", "classify", "sanitize"],
    },
    AgentRole.RANKER: {
        "name": "Ranker",
        "description": (
            "Scores hits by relevance, credibility, and freshness."
        ),
        "skill_id": "rank",
        "skill_description": (
            "Rank search hits by claim relevance, credibility, and freshness."
        ),
        "tags": ["rank", "score", "credibility"],
    },
    AgentRole.EVIDENCE_DEDUPLICATOR: {
        "name": "EvidenceDeduplicator",
        "description": (
            "Normalizes and deduplicates evidence with source"
            " independence tracking."
        ),
        "skill_id": "normalize",
        "skill_description": (
            "Deduplicate evidence and compute source independence."
        ),
        "tags": ["deduplicate", "normalize", "independence"],
    },
    AgentRole.ADVERSARY: {
        "name": "Adversary",
        "description": (
            "Devil's Advocate that seeks counter-evidence for"
            " tentatively supported claims."
        ),
        "skill_id": "adversarial_verify",
        "skill_description": (
            "Actively seek counter-evidence for supported claims."
        ),
        "tags": ["adversary", "counter-evidence", "challenge"],
    },
    AgentRole.CRITIC: {
        "name": "Critic",
        "description": "Evaluates report quality and suggests improvements.",
        "skill_id": "critique",
        "skill_description": (
            "Evaluate report quality and suggest improvements."
        ),
        "tags": ["critique", "quality", "evaluation"],
    },
    AgentRole.POSTPROCESSOR: {
        "name": "Postprocessor",
        "description": (
            "Renders citations, redacts PII, and formats outputs."
        ),
        "skill_id": "postprocess",
        "skill_description": (
            "Render citations, redact PII, format markdown/json outputs."
        ),
        "tags": ["postprocess", "citations", "format"],
    },
}
