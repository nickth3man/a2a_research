"""Progress events and queue helpers for real-time UI updates.

This module re-exports from split sub-modules for backward compatibility.
"""

from __future__ import annotations

from a2a_research.progress_bus import Bus
from a2a_research.progress_emit import (
    emit,
    emit_claim_verdict,
    emit_handoff,
    emit_llm_response,
    emit_prompt,
    emit_rate_limit,
    emit_tool_call,
)
from a2a_research.progress_types import (
    PROMPT_DETAIL_MAX_CHARS,
    ProgressEvent,
    ProgressGranularity,
    ProgressPhase,
    ProgressQueue,
    ProgressReporter,
    current_session_id,
    truncate_text,
    using_session,
)
from a2a_research.progress_utils import (
    create_progress_reporter,
    drain_progress_while_running,
)

__all__ = [
    "PROMPT_DETAIL_MAX_CHARS",
    "Bus",
    "ProgressEvent",
    "ProgressGranularity",
    "ProgressPhase",
    "ProgressQueue",
    "ProgressReporter",
    "create_progress_reporter",
    "current_session_id",
    "drain_progress_while_running",
    "emit",
    "emit_claim_verdict",
    "emit_handoff",
    "emit_llm_response",
    "emit_prompt",
    "emit_rate_limit",
    "emit_tool_call",
    "truncate_text",
    "using_session",
]
