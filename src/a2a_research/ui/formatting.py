"""Formatting utilities for UI components.

Reusable string transformation functions to decouple formatting logic from presentation.
"""


def format_source_display(src: str) -> str:
    """Format a source identifier for display.

    Normalizes source names by replacing underscores and hyphens with spaces,
    then converting to title case for human-readable display.

    Args:
        src: The raw source identifier (e.g., "arxiv_paper-2024").

    Returns:
        The formatted display name (e.g., "Arxiv Paper 2024").
    """
    return src.replace("_", " ").replace("-", " ").title()
