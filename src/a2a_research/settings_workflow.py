"""Workflow orchestration configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from a2a_research.settings_workflow_ab import ABTestingMixin
from a2a_research.settings_workflow_budget_search_ranking import (
    BudgetSearchRankingMixin,
)
from a2a_research.settings_workflow_evidence_adversary_verification import (
    EvidenceAdversaryVerificationMixin,
)
from a2a_research.settings_workflow_synthesis_output_checkpointing_pii import (
    SynthesisOutputCheckpointingPIIMixin,
)
from a2a_research.settings_workflow_telemetry import TelemetryMixin

__all__ = ["WorkflowConfig"]


class WorkflowConfig(
    BudgetSearchRankingMixin,
    EvidenceAdversaryVerificationMixin,
    SynthesisOutputCheckpointingPIIMixin,
    ABTestingMixin,
    TelemetryMixin,
    BaseSettings,
):
    """Workflow orchestration config (env prefix: ``WF_``).

    Fields map to ``WF_<SECTION>_<FIELD>`` in the environment.
    """

    model_config = SettingsConfigDict(
        env_prefix="WF_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
