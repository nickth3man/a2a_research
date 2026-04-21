"""Synthesizer core logic."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from a2a_research.agents.pydantic_ai.synthesizer import agent as _agent
from a2a_research.logging.app_logging import get_logger
from a2a_research.utils.citation_sanitize import sanitize_report_output
from a2a_research.models import AgentRole, Claim, ReportOutput, WebSource
from a2a_research.progress import (
    ProgressPhase,
    emit,
    emit_llm_response,
    emit_prompt,
)
from a2a_research.settings import settings as _app_settings

logger = get_logger(__name__)


def _build_prompt(
    query: str, claims: list[Claim], sources: list[WebSource]
) -> str:
    claim_block = (
        "\n".join(
            f"- [{c.verdict.value}] ({c.confidence:.2f}) {c.text}"
            f" sources={c.sources or []}"
            for c in claims
        )
        or "(no verified claims produced)"
    )
    source_block = (
        "\n".join(f"- {s.url} — {s.title}: {s.excerpt[:200]}" for s in sources)
        or "(no sources gathered)"
    )
    return (
        f"User query: {query}\n\n"
        f"Verified claims:\n{claim_block}\n\n"
        f"Sources:\n{source_block}\n\n"
        "Write the ReportOutput now."
    )


async def synthesize(
    query: str,
    claims: list[Claim],
    sources: list[WebSource],
    *,
    session_id: str = "",
) -> ReportOutput:
    """Run the Synthesizer agent and return the :class:`ReportOutput`."""
    agent = _agent.build_agent()
    emit(
        session_id,
        ProgressPhase.STEP_SUBSTEP,
        AgentRole.SYNTHESIZER,
        4,
        5,
        "building_prompt",
        detail=f"claims={len(claims)} sources={len(sources)}",
    )
    prompt = _build_prompt(query, claims, sources)
    emit_prompt(
        AgentRole.SYNTHESIZER,
        "synthesize",
        prompt,
        model=_app_settings.llm.model,
        session_id=session_id,
    )
    emit(
        session_id,
        ProgressPhase.STEP_SUBSTEP,
        AgentRole.SYNTHESIZER,
        4,
        5,
        "llm_call",
    )
    started = perf_counter()
    result = await agent.run(prompt)
    report = sanitize_report_output(result.output, sources, claims)
    try:
        preview = (
            result.output.model_dump_json()
            if hasattr(result.output, "model_dump_json")
            else str(result.output)
        )
    except Exception:
        preview = str(result.output)

    prompt_tokens = None
    completion_tokens = None
    finish_reason = ""
    usage_getter = getattr(result, "usage", None)
    if callable(usage_getter):
        usage = usage_getter()
        if usage:
            prompt_tokens = getattr(usage, "request_tokens", None) or getattr(
                usage, "prompt_tokens", None
            )
            completion_tokens = getattr(
                usage, "response_tokens", None
            ) or getattr(usage, "completion_tokens", None)

    emit_llm_response(
        AgentRole.SYNTHESIZER,
        "synthesize",
        preview,
        elapsed_ms=(perf_counter() - started) * 1000,
        model=_app_settings.llm.model,
        session_id=session_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        finish_reason=finish_reason,
    )
    return report
