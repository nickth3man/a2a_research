"""Structured error envelope for workflow diagnostics."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from core.models.enums import AgentRole  # noqa: TC001


class ErrorSeverity(StrEnum):
    FATAL = "fatal"
    WARNING = "warning"
    DEGRADED = "degraded"


class ErrorCode(StrEnum):
    QUERY_REJECTED = "QUERY_REJECTED"
    LOW_CLAIM_COVERAGE = "LOW_CLAIM_COVERAGE"
    PLANNER_EMPTY = "PLANNER_EMPTY"
    NO_HITS = "NO_HITS"
    ALL_URLS_FILTERED = "ALL_URLS_FILTERED"
    UNREADABLE_PAGES = "UNREADABLE_PAGES"
    BUDGET_EXHAUSTED_AFTER_GATHER = "BUDGET_EXHAUSTED_AFTER_GATHER"
    BUDGET_EXHAUSTED_AFTER_VERIFY = "BUDGET_EXHAUSTED_AFTER_VERIFY"
    BUDGET_EXHAUSTED_AFTER_SNAPSHOT = "BUDGET_EXHAUSTED_AFTER_SNAPSHOT"
    DIAGNOSTIC_SUMMARY = "DIAGNOSTIC_SUMMARY"


class ErrorEnvelope(BaseModel):
    role: AgentRole | None = None
    code: ErrorCode
    severity: ErrorSeverity
    retryable: bool = False
    root_cause: str = ""
    partial_results: dict[str, Any] = Field(default_factory=dict)
    remediation: str = ""
    trace_id: str = ""
    upstream_errors: list[ErrorEnvelope] = Field(default_factory=list)


ErrorEnvelope.model_rebuild()
