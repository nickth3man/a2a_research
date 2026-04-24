"""Tests for scripts/extract_prompts.py."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts/ to sys.path so we can import from there
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from extract_prompts import extract_prompts  # noqa: E402


class TestExtractPromptsV1:
    """Tests for the regex-based extract_prompts (v1)."""

    def test_no_change_when_no_triple_quoted(self, tmp_path: Path) -> None:
        py_file = tmp_path / "test_file.py"
        content = "x = 'short string'\ny = 42\n"
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts(py_file)
        assert result == 0
        assert py_file.read_text(encoding="utf-8") == content

    def test_no_change_when_triple_quoted_is_short(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "test_file.py"
        content = 'x = """short"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts(py_file)
        assert result == 0

    def test_extracts_long_triple_quoted_to_txt(self, tmp_path: Path) -> None:
        py_file = tmp_path / "test_file.py"
        long_content = "A" * 200
        content = f'my_prompt = """\n{long_content}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts(py_file)
        assert result == 1
        txt_file = tmp_path / "test_file_my_prompt.txt"
        assert txt_file.exists()
        new_py = py_file.read_text(encoding="utf-8")
        assert "test_file_my_prompt.txt" in new_py
        assert "read_text" in new_py

    def test_extracts_content_without_triple_quotes(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "test_file.py"
        long_inner = "Some long text " * 20
        content = f'prompt = """\n{long_inner}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        extract_prompts(py_file)
        txt_file = tmp_path / "test_file_prompt.txt"
        txt_content = txt_file.read_text(encoding="utf-8")
        assert '"""' not in txt_content

    def test_returns_count_of_extractions(self, tmp_path: Path) -> None:
        py_file = tmp_path / "test_file.py"
        long = "X" * 150
        content = f'a = """\n{long}\n"""\nb = """\n{long}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts(py_file)
        assert result >= 1

    def test_file_unchanged_when_no_extractions(self, tmp_path: Path) -> None:
        py_file = tmp_path / "test_file.py"
        content = "x = 1\n"
        py_file.write_text(content, encoding="utf-8")
        extract_prompts(py_file)
        assert py_file.read_text(encoding="utf-8") == content
