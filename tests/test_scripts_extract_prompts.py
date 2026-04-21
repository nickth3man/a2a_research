"""Tests for scripts/extract_prompts.py and scripts/extract_prompts_v2.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts/ to sys.path so we can import from there
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from extract_prompts import extract_prompts as extract_prompts_v1
from extract_prompts_v2 import extract_prompts as extract_prompts_v2


class TestExtractPromptsV1:
    """Tests for the regex-based extract_prompts (v1)."""

    def test_no_change_when_no_triple_quoted(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "test_file.py"
        content = "x = 'short string'\ny = 42\n"
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v1(py_file)
        assert result == 0
        assert py_file.read_text(encoding="utf-8") == content

    def test_no_change_when_triple_quoted_is_short(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "test_file.py"
        # A short triple-quoted string
        content = 'x = """short"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v1(py_file)
        assert result == 0

    def test_extracts_long_triple_quoted_to_txt(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "test_file.py"
        long_content = "A" * 200
        content = f'my_prompt = """\n{long_content}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v1(py_file)
        assert result == 1
        # The .txt file should be created
        txt_file = tmp_path / "test_file_my_prompt.txt"
        assert txt_file.exists()
        # The .py file should reference the .txt file
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
        extract_prompts_v1(py_file)
        txt_file = tmp_path / "test_file_prompt.txt"
        txt_content = txt_file.read_text(encoding="utf-8")
        assert '"""' not in txt_content

    def test_returns_count_of_extractions(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "test_file.py"
        long = "X" * 150
        content = f'a = """\n{long}\n"""\nb = """\n{long}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v1(py_file)
        # Both should be extracted
        assert result >= 1

    def test_file_unchanged_when_no_extractions(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "test_file.py"
        content = "x = 1\n"
        py_file.write_text(content, encoding="utf-8")
        extract_prompts_v1(py_file)
        assert py_file.read_text(encoding="utf-8") == content


class TestExtractPromptsV2:
    """Tests for the AST-based extract_prompts (v2)."""

    def test_no_extractions_for_short_strings(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        content = "x = 'hello'\ny = 'world'\n"
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v2(py_file)
        assert result == 0
        assert py_file.read_text(encoding="utf-8") == content

    def test_no_extractions_for_non_multiline_strings(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        # A long single-line string but no newline in it
        content = f'x = "{"A" * 200}"\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v2(py_file)
        assert result == 0

    def test_extracts_multiline_string_over_100_chars(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        long_text = "line one\n" + ("More text " * 15)
        content = f'PROMPT = """\n{long_text}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v2(py_file)
        assert result == 1
        txt_file = tmp_path / "module_PROMPT.txt"
        assert txt_file.exists()

    def test_txt_file_contains_original_content(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        inner = "Important line\n" + "Details " * 15
        content = f'MY_VAR = """\n{inner}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        extract_prompts_v2(py_file)
        txt_file = tmp_path / "module_MY_VAR.txt"
        txt_content = txt_file.read_text(encoding="utf-8")
        assert "Important line" in txt_content

    def test_path_import_added_when_missing(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        inner = "A" * 50 + "\n" + "B" * 60
        content = f'MY_PROMPT = """\n{inner}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        extract_prompts_v2(py_file)
        new_content = py_file.read_text(encoding="utf-8")
        assert "from pathlib import Path" in new_content

    def test_path_import_not_duplicated_when_already_present(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        inner = "A" * 50 + "\n" + "B" * 60
        content = f'from pathlib import Path\nMY_PROMPT = """\n{inner}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        extract_prompts_v2(py_file)
        new_content = py_file.read_text(encoding="utf-8")
        # Should not duplicate the import
        assert new_content.count("from pathlib import Path") == 1

    def test_py_file_references_txt_file(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        inner = "A" * 50 + "\n" + "B" * 60
        content = f'MY_VAR = """\n{inner}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        extract_prompts_v2(py_file)
        new_py = py_file.read_text(encoding="utf-8")
        assert "module_MY_VAR.txt" in new_py
        assert "read_text" in new_py

    def test_returns_count_of_extractions(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        inner = "A" * 50 + "\n" + "B" * 60
        content = f'VAR1 = """\n{inner}\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v2(py_file)
        assert result == 1

    def test_does_not_extract_short_multiline_string(
        self, tmp_path: Path
    ) -> None:
        py_file = tmp_path / "module.py"
        # Multiline but under 100 characters total
        content = 'SHORT = """\nA\nB\n"""\n'
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v2(py_file)
        assert result == 0

    def test_ignores_non_name_targets(
        self, tmp_path: Path
    ) -> None:
        """List element or attribute assignments are not extracted."""
        py_file = tmp_path / "module.py"
        inner = "A" * 50 + "\n" + "B" * 60
        # An augmented assign target (not ast.Name) — uses regular assign
        # but with subscript target which has len(targets)==1 but not Name
        content = (
            "d = {}\n"
            f'd["key"] = """\n{inner}\n"""\n'
        )
        py_file.write_text(content, encoding="utf-8")
        result = extract_prompts_v2(py_file)
        # Subscript targets are not ast.Name, so should not be extracted
        assert result == 0