"""Hypothesis composite strategies for domain model objects.

Each strategy produces *valid* objects that satisfy Pydantic / dataclass
constraints.  Import these in property tests (T9-T12) via::

    from tests.property.fixtures import (
        claim_strategy,
        dag_strategy,
        budget_strategy,
        verdict_strategy,
        workflow_budget_strategy,
    )
"""

from __future__ import annotations

import hypothesis.strategies as st

from a2a_research.backend.core.models.claims import (
    Claim,
    ClaimDAG,
    ClaimDependency,
    FreshnessWindow,
)
from a2a_research.backend.core.models.enums import Verdict
from a2a_research.backend.core.models.workflow import (
    BudgetConsumption,
    WorkflowBudget,
)


# ---------------------------------------------------------------------------
# Primitive helpers
# ---------------------------------------------------------------------------

_claim_id = st.from_regex(r"clm_[a-f0-9]{8}", fullmatch=True)
_short_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Zs"),
        whitelist_characters=" ",
    ),
    min_size=1,
    max_size=120,
)
_relation = st.sampled_from(["presupposes", "refines", "contrasts"])


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


@st.composite
def verdict_strategy(draw: st.DrawFn) -> Verdict:
    """Generate a random valid Verdict enum value."""
    return draw(st.sampled_from(list(Verdict)))


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------


@st.composite
def claim_strategy(draw: st.DrawFn) -> Claim:
    """Generate a valid Claim with constrained fields."""
    claim_id = draw(_claim_id)
    text = draw(_short_text)
    max_age = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=365)))
    strict = draw(st.booleans())
    confidence = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    verdict = draw(verdict_strategy())
    sources = draw(st.lists(_short_text, max_size=5))
    snippets = draw(st.lists(_short_text, max_size=5))

    return Claim(
        id=claim_id,
        text=text,
        freshness=FreshnessWindow(
            max_age_days=max_age,
            strict=strict,
            rationale="",
        ),
        confidence=confidence,
        verdict=verdict,
        sources=sources,
        evidence_snippets=snippets,
    )


# ---------------------------------------------------------------------------
# ClaimDAG
# ---------------------------------------------------------------------------


@st.composite
def dag_strategy(draw: st.DrawFn) -> ClaimDAG:
    """Generate a valid ClaimDAG (acyclic by construction).

    Nodes are generated first, then edges only go from lower-index to
    higher-index nodes, guaranteeing no cycles.
    """
    node_count = draw(st.integers(min_value=0, max_value=8))
    nodes = draw(
        st.lists(
            _claim_id,
            min_size=node_count,
            max_size=node_count,
            unique=True,
        )
    )

    edges: list[ClaimDependency] = []
    if node_count >= 2:
        edge_count = draw(st.integers(min_value=0, max_value=node_count - 1))
        for _ in range(edge_count):
            parent_idx = draw(st.integers(min_value=0, max_value=node_count - 2))
            child_idx = draw(
                st.integers(min_value=parent_idx + 1, max_value=node_count - 1)
            )
            relation = draw(_relation)
            edges.append(
                ClaimDependency(
                    parent_id=nodes[parent_idx],
                    child_id=nodes[child_idx],
                    relation=relation,
                )
            )

    return ClaimDAG(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# BudgetConsumption (dataclass)
# ---------------------------------------------------------------------------


@st.composite
def budget_strategy(draw: st.DrawFn) -> BudgetConsumption:
    """Generate a valid BudgetConsumption dataclass."""
    return BudgetConsumption(
        rounds=draw(st.integers(min_value=0, max_value=50)),
        tokens_consumed=draw(st.integers(min_value=0, max_value=500_000)),
        wall_seconds=draw(
            st.floats(
                min_value=0.0, max_value=3600.0,
                allow_nan=False, allow_infinity=False,
            )
        ),
        http_calls=draw(st.integers(min_value=0, max_value=200)),
        urls_fetched=draw(st.integers(min_value=0, max_value=100)),
        critic_revision_loops=draw(st.integers(min_value=0, max_value=10)),
    )


# ---------------------------------------------------------------------------
# WorkflowBudget (Pydantic BaseModel)
# ---------------------------------------------------------------------------


@st.composite
def workflow_budget_strategy(draw: st.DrawFn) -> WorkflowBudget:
    """Generate a valid WorkflowBudget model."""
    return WorkflowBudget(
        max_rounds=draw(st.integers(min_value=1, max_value=20)),
        max_tokens=draw(st.integers(min_value=1000, max_value=1_000_000)),
        max_wall_seconds=draw(
            st.floats(
                min_value=1.0, max_value=7200.0,
                allow_nan=False, allow_infinity=False,
            )
        ),
        max_http_calls=draw(st.integers(min_value=1, max_value=500)),
        max_urls_fetched=draw(st.integers(min_value=1, max_value=200)),
        min_marginal_evidence=draw(st.integers(min_value=0, max_value=10)),
        max_critic_revision_loops=draw(st.integers(min_value=0, max_value=10)),
    )
