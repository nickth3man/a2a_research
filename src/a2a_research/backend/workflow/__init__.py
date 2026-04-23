"""Research workflow orchestrator."""

from __future__ import annotations

from a2a_research.backend.workflow.workflow_engine import (
    run_workflow_async,
    run_workflow_sync,
)

# Backward-compatible alias
run_research_async = run_workflow_async

__all__ = [
    "run_workflow_async",
    "run_workflow_sync",
    "run_research_async",
]
