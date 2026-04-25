"""LLM provider exception types."""

from __future__ import annotations


class ProviderRequestError(RuntimeError):
    """Base error for upstream provider request failures."""


class ProviderRateLimitError(ProviderRequestError):
    """Transient upstream rate limit error."""
