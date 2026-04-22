"""System prompts for the Adversary nodes."""

from __future__ import annotations

from pathlib import Path

INVERSION_QUERY_PROMPT = (
    Path(__file__).parent / "prompt_INVERSION_QUERY_PROMPT.txt"
).read_text(encoding="utf-8")


EVALUATE_EVIDENCE_PROMPT = (
    Path(__file__).parent / "prompt_EVALUATE_EVIDENCE_PROMPT.txt"
).read_text(encoding="utf-8")


CHALLENGE_PROMPT = (
    Path(__file__).parent / "prompt_CHALLENGE_PROMPT.txt"
).read_text(encoding="utf-8")
