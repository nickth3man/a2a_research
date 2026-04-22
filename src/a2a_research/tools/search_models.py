"""Search models and data structures."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebHit(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""
    source: str = Field(
        default="unknown",
        description=(
            "Single provider id or comma-sorted ids when merged "
            "(tavily, brave, duckduckgo)."
        ),
    )
    score: float = Field(default=0.0, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Parallel search outcome for a single query."""

    hits: list[WebHit] = Field(default_factory=list)
    errors: list[str] = Field(
        default_factory=list,
        description=(
            "Per-provider failure reasons (one human-readable string "
            "per failed provider)."
        ),
    )
    providers_attempted: list[str] = Field(default_factory=list)
    providers_successful: list[str] = Field(default_factory=list)

    @property
    def any_provider_succeeded(self) -> bool:
        return bool(self.providers_successful)


__all__ = ["SearchResult", "WebHit"]
