"""Tests for Synthesizer citation allowlist enforcement."""

from __future__ import annotations

from a2a_research.utils.citation_sanitize import (
    allowed_urls_from_evidence,
    normalize_url,
    sanitize_report_output,
)
from a2a_research.models import (
    Citation,
    Claim,
    ReportOutput,
    ReportSection,
    Verdict,
    WebSource,
)


def test_normalize_url_strips_www_and_trailing_slash() -> None:
    a = normalize_url("https://WWW.Example.COM/path/to/")
    b = normalize_url("https://example.com/path/to")
    assert a == b


def test_allowed_urls_from_evidence() -> None:
    sources = [WebSource(url="https://good.example/a", title="A")]
    claims = [
        Claim(
            text="x",
            verdict=Verdict.SUPPORTED,
            sources=["https://claim.only/page"],
        )
    ]
    allowed = allowed_urls_from_evidence(sources, claims)
    assert "https://good.example/a" in allowed
    assert "https://claim.only/page" in allowed


def test_sanitize_drops_hallucinated_citations() -> None:
    report = ReportOutput(
        title="T",
        summary="See [bad](https://evil.test/x).",
        sections=[
            ReportSection(
                heading="H",
                body="Ref [x](https://evil.test/y).",
                citations=[
                    Citation(url="https://real.example/doc", title="ok"),
                    Citation(
                        url="https://fake.example/hallucination", title="bad"
                    ),
                ],
            )
        ],
        citations=[Citation(url="https://also.fake/", title="nope")],
    )
    sources = [WebSource(url="https://real.example/doc", title="Real")]
    claims: list[Claim] = []
    out = sanitize_report_output(report, sources, claims)
    assert len(out.citations) == 0
    assert len(out.sections[0].citations) == 1
    assert out.sections[0].citations[0].url == "https://real.example/doc"
    assert "evil.test" not in out.summary
    assert "evil.test" not in out.sections[0].body


def test_sanitize_keeps_claim_source_urls() -> None:
    report = ReportOutput(
        title="T",
        summary="OK",
        sections=[],
        citations=[Citation(url="https://from.claim/x", title="c")],
    )
    sources: list[WebSource] = []
    claims = [
        Claim(
            text="q",
            verdict=Verdict.SUPPORTED,
            sources=["https://from.claim/x"],
        )
    ]
    out = sanitize_report_output(report, sources, claims)
    assert len(out.citations) == 1
