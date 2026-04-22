"""Agent definitions, step indices, timeouts, and budget helpers.

Provides the canonical agent registry used by both the v1 coordinator
and the v2 claim-centric workflow engine.
"""

from __future__ import annotations

from a2a_research.backend.core.models import (
    AgentCapability,
    AgentDefinition,
    AgentRole,
    WorkflowBudget,
)
from a2a_research.backend.core.settings import settings

__all__ = [
    "AGENT_DEFINITIONS",
    "STEP_INDEX_V2",
    "TOTAL_STEPS_V2",
    "budget_from_settings",
    "stage_timeout",
]

AGENT_DEFINITIONS: dict[AgentRole, AgentDefinition] = {
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

STEP_INDEX_V2: dict[AgentRole, int] = {
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

TOTAL_STEPS_V2 = len(STEP_INDEX_V2)

PER_STAGE_TIMEOUTS: dict[AgentRole, float] = {
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


def budget_from_settings() -> WorkflowBudget:
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


def stage_timeout(role: AgentRole) -> float:
    return PER_STAGE_TIMEOUTS.get(role, 30.0)
