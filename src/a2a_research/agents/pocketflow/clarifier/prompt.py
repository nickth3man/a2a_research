"""System prompts for the Clarifier nodes."""

from __future__ import annotations

from pathlib import Path

__all__ = ["AUDIT_PROMPT", "DISAMBIGUATE_PROMPT"]


DISAMBIGUATE_PROMPT = (
    Path(__file__).parent / "prompt_DISAMBIGUATE_PROMPT.txt"
).read_text(encoding="utf-8")


AUDIT_PROMPT = (Path(__file__).parent / "prompt_AUDIT_PROMPT.txt").read_text(
    encoding="utf-8"
)
