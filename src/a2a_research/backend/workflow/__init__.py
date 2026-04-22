"""Top-level research workflow orchestrator.

Two modes:
- v1 (default): Linear 5-agent pipeline via :func:`run_research_async`.
- v2 (claim-centric): Full workflow engine via
  :func:`run_workflow_v2_async`.
"""

from __future__ import annotations

from a2a_research.backend.workflow.coordinator import (
    run_research,
    run_research_async,
    run_research_sync,
)
from a2a_research.backend.workflow.workflow_engine import (
    run_workflow_v2_async,
    run_workflow_v2_sync,
)

__all__ = [
    "run_research",
    "run_research_async",
    "run_research_sync",
    "run_workflow_v2_async",
    "run_workflow_v2_sync",
]
