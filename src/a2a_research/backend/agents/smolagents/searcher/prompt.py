from pathlib import Path

"""System prompt for the Searcher."""

SEARCHER_PROMPT = (
    Path(__file__).parent / "prompt_SEARCHER_PROMPT.txt"
).read_text(encoding="utf-8")
