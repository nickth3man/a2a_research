"""PocketFlow nodes for the Adversary agent.

This module re-exports from split sub-modules for backward compatibility.
"""

from __future__ import annotations

from a2a_research.backend.agents.pocketflow.adversary.nodes_challenge import (
    ChallengeNode,
    ChallengeResult,
)
from a2a_research.backend.agents.pocketflow.adversary.nodes_evaluate import (
    EvaluateEvidenceNode,
)
from a2a_research.backend.agents.pocketflow.adversary.nodes_inversion import (
    GenerateInversionQueriesNode,
    TerminalNode,
)

__all__ = [
    "ChallengeNode",
    "ChallengeResult",
    "EvaluateEvidenceNode",
    "GenerateInversionQueriesNode",
    "TerminalNode",
]
