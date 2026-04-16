"""Shared utilities for PocketFlow agents.

Splits by concern:

- :mod:`llm`            — LLM invocation (single patch point for tests)
- :mod:`sanitize`       — input query normalisation
- :mod:`progress`       — substep progress-event helpers
- :mod:`fallbacks`      — deterministic fallbacks for provider failures
- :mod:`results`        — :class:`AgentResult` construction
- :mod:`shared_store`   — Shared Store schema
- :mod:`helpers`        — deterministic output parsing and markdown formatting
- :mod:`registry`       — :class:`AgentRegistry`, :class:`AgentSpec`, ``register_agent``
- :mod:`nodes`          — generic :class:`ActorNode` base + ``create_actor_node`` factory
- :mod:`actor_helpers`  — role\u2192agent-utils dispatcher for payload/sender lookup
- :mod:`policy`         — :class:`PipelineOrderPolicy`
- :mod:`adapter`        — :class:`SyncWorkflowAdapter` (``invoke``/``ainvoke`` wrappers)
- :mod:`coordinator`    — legacy linear 4-role :class:`AsyncFlow` builder
"""

from __future__ import annotations

from a2a_research.agents.pocketflow.utils.fallbacks import (
    fallback_research_summary,
    fallback_verified_claims,
)
from a2a_research.agents.pocketflow.utils.helpers import (
    aggregate_citations,
    build_markdown_report,
    create_result,
    extract_claims_from_llm_output,
    extract_report_markdown,
    extract_research_summary,
    format_claim_verdict,
    format_claims_section,
    format_confidence,
    normalize_claim_id,
    parse_json_safely,
)
from a2a_research.agents.pocketflow.utils.progress import (
    create_substep_emitter,
    extract_progress_context,
)
from a2a_research.agents.pocketflow.utils.results import create_agent_result
from a2a_research.agents.pocketflow.utils.sanitize import sanitize_query
from a2a_research.agents.pocketflow.utils.shared_store import build_shared_store

__all__ = [
    "aggregate_citations",
    "build_markdown_report",
    "build_shared_store",
    "create_agent_result",
    "create_result",
    "create_substep_emitter",
    "extract_claims_from_llm_output",
    "extract_progress_context",
    "extract_report_markdown",
    "extract_research_summary",
    "fallback_research_summary",
    "fallback_verified_claims",
    "format_claim_verdict",
    "format_claims_section",
    "format_confidence",
    "normalize_claim_id",
    "parse_json_safely",
    "sanitize_query",
]
