"""Mocked Tavily search tests — no live API calls."""

from __future__ import annotations

import pytest

from a2a_research.backend.tools import search as search_module
from a2a_research.backend.tools.search import WebHit, web_search


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hit(
    url: str = "https://example.com",
    title: str = "Example",
    snippet: str = "A snippet.",
    source: str = "tavily",
    score: float = 0.9,
) -> WebHit:
    return WebHit(url=url, title=title, snippet=snippet, source=source, score=score)


# ---------------------------------------------------------------------------
# 1. test_tavily_search_returns_hits
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_search_returns_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([_make_hit()], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("test query")
    assert len(result.hits) >= 1
    assert result.hits[0].source == "tavily"


# ---------------------------------------------------------------------------
# 2. test_tavily_hit_structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_hit_structure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(
                    url="https://structured.example",
                    title="Structured Hit",
                    snippet="Detailed snippet text",
                    source="tavily",
                    score=0.85,
                )
            ],
            None,
        )

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("structure check")
    hit = result.hits[0]
    assert hit.url == "https://structured.example"
    assert hit.title == "Structured Hit"
    assert hit.snippet == "Detailed snippet text"
    assert hit.source == "tavily"
    assert hit.score == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# 3. test_tavily_max_results_respected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_max_results_respected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        hits = [_make_hit(url=f"https://h{i}.example") for i in range(5)]
        return (hits[:n], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("truncation", max_results=3)
    assert len(result.hits) <= 3


# ---------------------------------------------------------------------------
# 4. test_tavily_score_positive
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_score_positive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                _make_hit(url="https://s1.example", score=0.1),
                _make_hit(url="https://s2.example", score=0.99),
            ],
            None,
        )

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("scores")
    for hit in result.hits:
        assert hit.score > 0


# ---------------------------------------------------------------------------
# 5. test_tavily_unicode_query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_unicode_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_queries: list[str] = []

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        captured_queries.append(q)
        return ([_make_hit()], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("München Germany history")
    assert len(result.hits) >= 1
    assert captured_queries[0] == "München Germany history"


# ---------------------------------------------------------------------------
# 6. test_tavily_popular_query
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_popular_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        hits = [
            _make_hit(url=f"https://pop{i}.example", score=0.9 - i * 0.1)
            for i in range(5)
        ]
        return (hits, None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("popular query", max_results=10)
    assert len(result.hits) >= 5


# ---------------------------------------------------------------------------
# 7. test_web_search_merges_providers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_web_search_merges_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([_make_hit(url="https://tav.example", source="tavily")], None)

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([_make_hit(url="https://brave.example", source="brave", score=0.8)], None)

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([_make_hit(url="https://ddg.example", source="duckduckgo", score=0.7)], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    result = await web_search("merge test", max_results=10)
    urls = {h.url for h in result.hits}
    assert "https://tav.example" in urls
    assert "https://brave.example" in urls
    assert "https://ddg.example" in urls


# ---------------------------------------------------------------------------
# 8. test_web_search_deduplication
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_web_search_deduplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dup_url = "https://dup.example"

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([_make_hit(url=dup_url, source="tavily", score=0.9)], None)

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([_make_hit(url=dup_url, source="brave", score=0.8)], None)

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([_make_hit(url=dup_url, source="duckduckgo", score=0.7)], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    result = await web_search("dedup test", max_results=10)
    urls = [h.url for h in result.hits]
    # The same URL should appear only once after merge
    assert urls.count(dup_url) == 1


# ---------------------------------------------------------------------------
# 9. test_tavily_error_handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_error_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], "API error")

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("error test")
    assert any("API error" in e for e in result.errors)


# ---------------------------------------------------------------------------
# 10. test_tavily_empty_results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_empty_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("empty test")
    # No Tavily-specific error — just no hits from Tavily
    tavily_errors = [e for e in result.errors if "tavily" in e.lower()]
    assert tavily_errors == []


# ---------------------------------------------------------------------------
# 11. test_tavily_timeout_error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], "Request timed out")

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("timeout test")
    assert any("timed out" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# 12. test_tavily_malformed_response
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_malformed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], "Malformed JSON")

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("malformed test")
    assert any("malformed" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# 13. test_tavily_query_passthrough
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tavily_query_passthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        captured.append(q)
        return ([_make_hit()], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    await web_search("exact query passthrough")
    assert captured == ["exact query passthrough"]


# ---------------------------------------------------------------------------
# Shared empty provider (avoids repeating in every test)
# ---------------------------------------------------------------------------

async def _empty_provider(q: str, n: int) -> tuple[list[WebHit], str | None]:
    return ([], None)
