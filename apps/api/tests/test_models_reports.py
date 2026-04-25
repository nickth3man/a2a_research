"""Tests for core.models.reports — ReportOutput.to_markdown."""

from __future__ import annotations

from core.models.reports import Citation, ReportOutput, ReportSection


class TestReportOutputToMarkdown:
    def test_basic_report_no_sections_no_citations(self) -> None:
        report = ReportOutput(
            title="Test Report", summary="A summary of findings."
        )
        md = report.to_markdown()
        assert "# Test Report" in md
        assert "A summary of findings." in md
        assert "## Sources" not in md

    def test_with_sections(self) -> None:
        report = ReportOutput(
            title="T",
            summary="S",
            sections=[
                ReportSection(
                    heading="Section 1", body="Body of section one."
                ),
                ReportSection(
                    heading="Section 2", body="Body of section two."
                ),
            ],
        )
        md = report.to_markdown()
        assert "## Section 1" in md
        assert "Body of section one." in md
        assert "## Section 2" in md
        assert "Body of section two." in md

    def test_with_citations(self) -> None:
        report = ReportOutput(
            title="T",
            summary="S",
            citations=[
                Citation(url="https://a.com", title="Source A"),
                Citation(url="https://b.com"),
            ],
        )
        md = report.to_markdown()
        assert "## Sources" in md
        assert "[Source A](https://a.com)" in md
        assert "[https://b.com](https://b.com)" in md

    def test_full_report_with_sections_and_citations(self) -> None:
        report = ReportOutput(
            title="Full Report",
            summary="Full summary.",
            sections=[
                ReportSection(heading="Intro", body="Welcome.", citations=[]),
            ],
            citations=[
                Citation(url="https://x.com", title="X"),
            ],
        )
        md = report.to_markdown()
        assert "# Full Report" in md
        assert "Full summary." in md
        assert "## Intro" in md
        assert "Welcome." in md
        assert "## Sources" in md
        assert "[X](https://x.com)" in md

    def test_sections_body_is_stripped(self) -> None:
        report = ReportOutput(
            title="T",
            summary="S",
            sections=[
                ReportSection(heading="H", body="  padded body  \n"),
            ],
        )
        md = report.to_markdown()
        assert "padded body" in md
        assert "  padded body  " not in md
