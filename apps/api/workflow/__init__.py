"""Research workflow orchestrator."""

from __future__ import annotations

from typing import Any

# Import from leaf modules to avoid circular imports
from workflow.claims import claims_to_process, should_abort_preprocessing
from workflow.coerce import (
    coerce_claims,
    coerce_dag,
    coerce_evidence_unit,
    coerce_page_content,
    coerce_web_hit,
    payload,
    task_failed,
)
from workflow.status import emit_envelope, emit_step, set_status
from workflow.workflow_engine import (
    run_workflow_async,
    run_workflow_sync,
)

# Backward-compatible aliases
run_research_async = run_workflow_async
run_research_sync = run_workflow_sync

# Lazily-imported names to avoid circular imports.
# Sub-modules (engine_final, engine_gather, etc.) import these
# from "workflow" → resolved via __getattr__ below.

_LAZY_IMPORTS: dict[str, str] = {
    "run_agent": "workflow.agents",
    "run_search_stage": "workflow.engine_gather_search",
    "run_evidence_loop": "workflow.engine_loop_impl",
    "gather_evidence": "workflow.engine_gather",
    "run_replan": "workflow.engine_replan",
    "run_verify": "workflow.engine_verify",
    "update_provenance": "workflow.engine_provenance",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        mod = importlib.import_module(_LAZY_IMPORTS[name])
        attr = getattr(mod, name)
        globals()[name] = attr
        return attr
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "claims_to_process",
    "coerce_claims",
    "coerce_dag",
    "coerce_evidence_unit",
    "coerce_page_content",
    "coerce_web_hit",
    "emit_envelope",
    "emit_step",
    "gather_evidence",
    "payload",
    "run_agent",
    "run_evidence_loop",
    "run_replan",
    "run_research_async",
    "run_research_sync",
    "run_search_stage",
    "run_verify",
    "run_workflow_async",
    "run_workflow_sync",
    "set_status",
    "should_abort_preprocessing",
    "task_failed",
    "update_provenance",
]
