"""Constrain Synthesizer output so citations only reference real pipeline URLs.

The LLM is instructed not to invent links, but structured output is not
validated by the model. We enforce an allowlist built from ``WebSource`` rows
and URL strings attached to verified claims.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

from a2a_research.logging.app_logging import get_logger
from a2a_research.models import (
    Citation,
    Claim,
    ReportOutput,
    ReportSection,
    WebSource,
)

logger = get_logger(__name__)

__all__ = [
    "allowed_urls_from_evidence",
    "normalize_url",
    "sanitize_report_output",
]

_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (scheme/host/path, no trailing slash on"""
    """path)."""
    raw = url.strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return raw
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")
    return urlunparse((parsed.scheme.lower(), host, path, "", "", ""))


def allowed_urls_from_evidence(
    sources: list[WebSource], claims: list[Claim]
) -> frozenset[str]:
    """URLs that may appear in the final report."""
    out: set[str] = set()
    for s in sources:
        u = (s.url or "").strip()
        if not u:
            continue
        out.add(u)
        nu = normalize_url(u)
        if nu:
            out.add(nu)
    for c in claims:
        for u in c.sources:
            u = (u or "").strip()
            if not u.startswith(("http://", "https://")):
                continue
            out.add(u)
            nu = normalize_url(u)
            if nu:
                out.add(nu)
    return frozenset(out)


def _url_allowed(candidate: str, allowed: frozenset[str]) -> bool:
    c = candidate.strip()
    if not c:
        return False
    if c in allowed:
        return True
    n = normalize_url(c)
    return bool(n) and n in allowed


def _filter_citations(
    citations: list[Citation], allowed: frozenset[str]
) -> list[Citation]:
    kept: list[Citation] = []
    for cit in citations:
        if _url_allowed(cit.url, allowed):
            kept.append(cit)
    return kept


def _strip_untrusted_markdown_links(text: str, allowed: frozenset[str]) -> str:
    """Replace ``[label](url)`` with ``label`` when ``url`` is not in the"""
    """allowlist."""

    def repl(m: re.Match[str]) -> str:
        label, url = m.group(1), m.group(2).strip()
        if _url_allowed(url, allowed):
            return m.group(0)
        return label

    return _MD_LINK.sub(repl, text)


def sanitize_report_output(
    report: ReportOutput,
    sources: list[WebSource],
    claims: list[Claim],
) -> ReportOutput:
    """Drop hallucinated citations and strip bad markdown links from prose."""
    allowed = allowed_urls_from_evidence(sources, claims)
    if not allowed:
        logger.warning(
            "citation_sanitize: empty allowlist; dropping all"
            " structured citations"
        )
        empty: frozenset[str] = frozenset()
        return report.model_copy(
            update={
                "citations": [],
                "sections": [
                    ReportSection(
                        heading=s.heading,
                        body=_strip_untrusted_markdown_links(s.body, empty),
                        citations=[],
                    )
                    for s in report.sections
                ],
                "summary": _strip_untrusted_markdown_links(
                    report.summary, empty
                ),
            }
        )

    before_top = len(report.citations)
    new_top = _filter_citations(list(report.citations), allowed)

    new_sections: list[ReportSection] = []
    dropped_sec = 0
    for sec in report.sections:
        before = len(sec.citations)
        filt = _filter_citations(list(sec.citations), allowed)
        dropped_sec += before - len(filt)
        new_sections.append(
            ReportSection(
                heading=sec.heading,
                body=_strip_untrusted_markdown_links(sec.body, allowed),
                citations=filt,
            )
        )

    new_summary = _strip_untrusted_markdown_links(report.summary, allowed)
    dropped_top = before_top - len(new_top)
    if dropped_top or dropped_sec:
        logger.info(
            "citation_sanitize: dropped %s top-level and %s section"
            " citations (allowlist size=%s)",
            dropped_top,
            dropped_sec,
            len(allowed),
        )

    return report.model_copy(
        update={
            "citations": new_top,
            "sections": new_sections,
            "summary": new_summary,
        }
    )
