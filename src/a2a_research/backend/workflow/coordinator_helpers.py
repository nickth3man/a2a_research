"""Helper functions for the v1 coordinator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from a2a.types import TaskState
from pydantic import ValidationError

from a2a_research.backend.core.a2a import extract_data_payload_or_warn
from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    Claim,
    ReportOutput,
    ResearchSession,
)
from a2a_research.backend.tools import PageContent, WebHit

if TYPE_CHECKING:
    from a2a_research.backend.core.progress import ProgressPhase

logger = get_logger(__name__)

__all__ = [
    "coerce_claim",
    "coerce_page_content",
    "coerce_report",
    "coerce_web_hit",
    "emit_role_event",
    "error_report",
    "mark_running_failed",
    "payload",
    "planner_failed_report",
    "set_status",
    "task_failed",
]

_TOTAL_STEPS = 12
_STEP_INDEX = {
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


def task_failed(task: Any) -> bool:
    status = getattr(task, "status", None)
    state = getattr(status, "state", None)
    return state == TaskState.TASK_STATE_FAILED


def planner_failed_report(query: str) -> str:
    return "\n".join(
        [
            "# Planner failed",
            "",
            f"**Query:** {query}",
            "",
            "The planner could not decompose this query into claims, "
            "so the pipeline stopped.",
            "",
        ]
    )


def error_report(query: str, reason: str, errors: list[str]) -> str:
    lines = [
        "# Research unavailable",
        "",
        f"**Query:** {query}",
        "",
        "The fact-checking pipeline could not gather web evidence, "
        "so no verified report was produced. The Synthesizer was "
        "skipped deliberately to avoid presenting unverified claims "
        "as fact.",
        "",
        "## Reason",
        "",
        reason,
    ]
    if errors:
        lines.extend(["", "## Provider-level errors", ""])
        lines.extend(f"- {err}" for err in errors)
    lines.extend(["", "## How to fix", ""])
    lines.append(
        "- Set `TAVILY_API_KEY` in `.env` (https://tavily.com/) and "
        "`BRAVE_API_KEY` (https://api-dashboard.search.brave.com/) "
        "if search providers are misconfigured."
    )
    lines.append(
        "- Wait and retry if DuckDuckGo rate-limited the request, "
        "or run behind a different egress."
    )
    lines.append(
        "- Re-run after verifying network connectivity to the "
        "search endpoints."
    )
    return "\n".join(lines) + "\n"


def payload(task: Any) -> dict[str, Any]:
    if task is None:
        return {}
    return extract_data_payload_or_warn(task)


def set_status(
    session: ResearchSession,
    role: AgentRole,
    status: AgentStatus,
    message: str,
) -> None:
    session.agent_results[role] = AgentResult(
        role=role, status=status, message=message
    )


def emit_role_event(
    session_id: str,
    role: AgentRole,
    phase: ProgressPhase,
    label: str,
    detail: str = "",
) -> None:
    from a2a_research.backend.core.progress import emit

    emit(
        session_id,
        phase,
        role,
        _STEP_INDEX[role],
        _TOTAL_STEPS,
        label,
        detail=detail,
    )


def mark_running_failed(session: ResearchSession) -> None:
    for role, result in list(session.agent_results.items()):
        if result.status == AgentStatus.RUNNING:
            session.agent_results[role] = result.model_copy(
                update={"status": AgentStatus.FAILED, "message": "Aborted."}
            )


def coerce_claim(raw: Any) -> Claim | None:
    if isinstance(raw, Claim):
        return raw
    if isinstance(raw, dict):
        try:
            return Claim.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Failed to coerce claim from payload: %s", exc)
            return None
    return None


def coerce_report(raw: Any) -> ReportOutput | None:
    if isinstance(raw, ReportOutput):
        return raw
    if isinstance(raw, dict):
        try:
            return ReportOutput.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Failed to coerce report from payload: %s", exc)
            return None
    return None


def coerce_web_hit(raw: Any) -> WebHit | None:
    if isinstance(raw, WebHit):
        return raw
    if isinstance(raw, dict):
        try:
            return WebHit.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Failed to coerce WebHit from payload: %s", exc)
            return None
    return None


def coerce_page_content(raw: Any) -> PageContent | None:
    if isinstance(raw, PageContent):
        return raw
    if isinstance(raw, dict):
        try:
            return PageContent.model_validate(raw)
        except ValidationError as exc:
            logger.warning(
                "Failed to coerce PageContent from payload: %s", exc
            )
            return None
    return None
