"""Merge hits from multiple search providers."""

from tools.search_models import WebHit

_SNIPPET_MERGE_SEP = "\n---\n"


def merge_hits_by_url(*lists: list[WebHit]) -> list[WebHit]:
    """Merge hits that share a URL: combine snippets, max score."""
    buckets: dict[str, list[WebHit]] = {}
    for lst in lists:
        for hit in lst:
            buckets.setdefault(hit.url, []).append(hit)
    merged: list[WebHit] = []
    for url, hits in buckets.items():
        sources: set[str] = set()
        for h in hits:
            for part in h.source.split(","):
                p = part.strip()
                if p:
                    sources.add(p)
        snippets: list[str] = []
        seen_snippet: set[str] = set()
        for h in hits:
            s = (h.snippet or "").strip()
            if s and s not in seen_snippet:
                seen_snippet.add(s)
                snippets.append(s)
        title = ""
        for h in hits:
            t = (h.title or "").strip()
            if len(t) > len(title):
                title = t
        score = max((h.score for h in hits), default=0.0)
        snippet = _SNIPPET_MERGE_SEP.join(snippets)
        source = ",".join(sorted(sources))
        merged.append(
            WebHit(
                url=url,
                title=title,
                snippet=snippet,
                source=source,
                score=score,
            )
        )
    return sorted(merged, key=lambda h: (-h.score, h.url))
