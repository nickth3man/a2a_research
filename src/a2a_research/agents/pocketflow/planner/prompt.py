from pathlib import Path

"""System prompts for the Planner nodes."""

CLASSIFIER_PROMPT = (
    Path(__file__).parent / "prompt_CLASSIFIER_PROMPT.txt"
).read_text(encoding="utf-8")


FACTUAL_PROMPT = (
    Path(__file__).parent / "prompt_FACTUAL_PROMPT.txt"
).read_text(encoding="utf-8")


COMPARATIVE_PROMPT = (
    Path(__file__).parent / "prompt_COMPARATIVE_PROMPT.txt"
).read_text(encoding="utf-8")


TEMPORAL_PROMPT = (
    Path(__file__).parent / "prompt_TEMPORAL_PROMPT.txt"
).read_text(encoding="utf-8")
