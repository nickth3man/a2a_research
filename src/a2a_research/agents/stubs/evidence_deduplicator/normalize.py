"""Normalize page dicts into evidence items."""

from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urlparse


def normalize_pages_to_evidence(
    pages: list[dict[str, Any]], existing_ids: set[str]
) -> list[dict[str, Any]]:
    """Convert raw page dicts into normalized evidence items."""
    new_evidence: list[dict[str, Any]] = []
    for p in pages:
        if not isinstance(p, dict):
            continue
        url = p.get("url", "")
        content = p.get("markdown", "")
        ev_id = hashlib.sha256(f"{url}:{content[:200]}".encode()).hexdigest()[
            :16
        ]
        if ev_id not in existing_ids:
            hostname = urlparse(url).hostname or ""
            publisher_id = hostname.removeprefix("www.")
            new_evidence.append(
                {
                    "id": ev_id,
                    "url": url,
                    "canonical_url": url,
                    "title": p.get("title", ""),
                    "source_type": "other",
                    "domain_authority": 0.5,
                    "publisher_id": publisher_id,
                    "syndication_cluster_id": None,
                    "published_at": None,
                    "fetched_at": "",
                    "content_hash": ev_id,
                    "main_text": content,
                    "quoted_passages": [
                        {
                            "id": f"psg_{ev_id[:8]}",
                            "evidence_id": ev_id,
                            "text": content[:500],
                            "claim_relevance_scores": {},
                            "is_quotation": False,
                        }
                    ],
                    "credibility_signals": {
                        "domain_reputation": 0.5,
                        "author_verified": False,
                        "has_citations": False,
                        "content_freshness_days": None,
                    },
                }
            )
    return new_evidence
