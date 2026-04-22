"""Report and citation models.

Models for web sources, inline citations, report sections, and the final
structured report output.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class WebSource(BaseModel):
    """A web resource discovered during research (URL-level citation)."""

    url: str
    title: str = ""
    excerpt: str = ""
    accessed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Citation(BaseModel):
    """Inline citation attached to a report section."""

    url: str
    title: str = ""
    quote: str = ""


class ReportSection(BaseModel):
    """A single section within a structured report."""

    heading: str
    body: str
    citations: list[Citation] = Field(default_factory=list)


class ReportOutput(BaseModel):
    """Structured final report produced by the Synthesizer."""

    title: str
    summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    def to_markdown(self) -> str:
        """Render the report as markdown (used by UI report panel)."""
        parts: list[str] = [
            f"# {self.title}",
            "",
            self.summary.strip(),
            "",
        ]
        for section in self.sections:
            parts.append(f"## {section.heading}")
            parts.append("")
            parts.append(section.body.strip())
            parts.append("")
        if self.citations:
            parts.append("## Sources")
            parts.append("")
            for i, c in enumerate(self.citations, 1):
                label = c.title or c.url
                parts.append(f"{i}. [{label}]({c.url})")
        return "\n".join(parts).strip() + "\n"
