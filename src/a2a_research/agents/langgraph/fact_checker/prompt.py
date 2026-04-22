from pathlib import Path

"""System prompts for the FactChecker verification loop."""

VERIFY_PROMPT = (Path(__file__).parent / "prompt_VERIFY_PROMPT.txt").read_text(
    encoding="utf-8"
)
