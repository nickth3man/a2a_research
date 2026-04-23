"""Research workflow orchestrator."""

from __future__ import annotations

from a2a_research.backend.workflow.workflow_engine import (
    run_workflow_async,
    run_workflow_sync,
)

# Backward-compatible aliases
run_research_async = run_workflow_async
run_research_sync = run_workflow_sync

__all__ = [
    "run_research_async",
    "run_research_sync",
    "run_workflow_async",
    "run_workflow_sync",
]
