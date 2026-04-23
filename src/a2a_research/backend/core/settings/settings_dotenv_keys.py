"""Expected .env keys for validation."""

from __future__ import annotations

from .settings_llm import LLMSettings
from .settings_validation import _expected_prefixed_keys
from .settings_workflow import WorkflowConfig

_EXPECTED_DOTENV_KEYS = {
    "LLM_PROVIDER",
    "LOG_LEVEL",
    "WORKFLOW_TIMEOUT",
    "TAVILY_API_KEY",
    "BRAVE_API_KEY",
    "SEARCH_MAX_RESULTS",
    "SEARCHER_MAX_STEPS",
    "RESEARCH_MAX_ROUNDS",
    "PREPROCESSOR_PORT",
    "CLARIFIER_PORT",
    "PLANNER_PORT",
    "SEARCHER_PORT",
    "RANKER_PORT",
    "READER_PORT",
    "EVIDENCE_DEDUPLICATOR_PORT",
    "FACT_CHECKER_PORT",
    "ADVERSARY_PORT",
    "SYNTHESIZER_PORT",
    "CRITIC_PORT",
    "POSTPROCESSOR_PORT",
    "PREPROCESSOR_URL",
    "CLARIFIER_URL",
    "PLANNER_URL",
    "SEARCHER_URL",
    "RANKER_URL",
    "READER_URL",
    "EVIDENCE_DEDUPLICATOR_URL",
    "FACT_CHECKER_URL",
    "ADVERSARY_URL",
    "SYNTHESIZER_URL",
    "CRITIC_URL",
    "POSTPROCESSOR_URL",
    *_expected_prefixed_keys(LLMSettings),
    *_expected_prefixed_keys(WorkflowConfig),
}
