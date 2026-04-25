from pathlib import Path

"""System prompt for the Reader."""

READER_PROMPT = (Path(__file__).parent / "prompt_READER_PROMPT.txt").read_text(
    encoding="utf-8"
)
