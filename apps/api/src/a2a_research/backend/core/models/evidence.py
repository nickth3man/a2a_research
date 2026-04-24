"""Evidence-related domain models.

Models for evidence units, passages, credibility signals, and source
independence tracking.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Passage(BaseModel):
    """A passage extracted from evidence."""

    id: str = Field(default_factory=lambda: f"psg_{uuid.uuid4().hex[:8]}")
    evidence_id: str
    text: str
    claim_relevance_scores: dict[str, float] = Field(default_factory=dict)
    is_quotation: bool = False


class CredibilitySignals(BaseModel):
    """Signals about evidence credibility."""

    domain_reputation: float = 0.0
    author_verified: bool = False
    has_citations: bool = False
    content_freshness_days: int | None = None


class EvidenceUnit(BaseModel):
    """Normalized evidence with stable IDs and source independence tracking."""

    id: str = Field(default_factory=lambda: f"evu_{uuid.uuid4().hex[:8]}")
    url: str
    canonical_url: str = ""
    title: str = ""
    source_type: Literal[
        "academic", "news", "blog", "wiki", "forum", "social", "other"
    ] = "other"
    domain_authority: float = 0.0
    publisher_id: str = ""
    syndication_cluster_id: str | None = None
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = ""
    main_text: str = ""
    quoted_passages: list[Passage] = Field(default_factory=list)
    credibility_signals: CredibilitySignals = Field(
        default_factory=CredibilitySignals
    )


class IndependenceGraph(BaseModel):
    """Tracks independent vs syndicated sources per claim."""

    claim_to_publishers: dict[str, set[str]] = Field(default_factory=dict)
    syndication_clusters: dict[str, list[str]] = Field(default_factory=dict)
    citation_chains: dict[str, list[str]] = Field(default_factory=dict)

    def independent_source_count(self, claim_id: str) -> int:
        """Distinct publishers after collapsing syndication clusters."""
        publishers = self.claim_to_publishers.get(claim_id, set())
        return len(publishers)

    def update(self, evidence_units: list[EvidenceUnit]) -> None:
        """Ingest new evidence and update publisher mappings."""
        for ev in evidence_units:
            if ev.syndication_cluster_id:
                members = self.syndication_clusters.setdefault(
                    ev.syndication_cluster_id, []
                )
                if ev.id not in members:
                    members.append(ev.id)
            for passage in ev.quoted_passages:
                for claim_id in passage.claim_relevance_scores:
                    if claim_id not in self.claim_to_publishers:
                        self.claim_to_publishers[claim_id] = set()
                    if ev.publisher_id:
                        self.claim_to_publishers[claim_id].add(ev.publisher_id)
