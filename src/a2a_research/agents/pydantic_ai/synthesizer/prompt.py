from pathlib import Path

"""System prompt for the Synthesizer."""

SYNTHESIZER_PROMPT = (
    Path(__file__).parent / "prompt_SYNTHESIZER_PROMPT.txt"
).read_text(encoding="utf-8")
