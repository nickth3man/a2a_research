"""
Test Python source constraints: max file size (lines)
and max line width (chars).

Scans ``src/`` and ``tests/`` recursively with no path exclusions.

Non-empty line counts: **soft** target ``SOFT_LIMIT``,
**hard** failure ``HARD_LIMIT``.

Physical line width is limited to ``MAX_LINE_CHAR_LIMIT``
characters (aligned with Ruff).
"""

from pathlib import Path

import pytest

# --- Configuration: file size (non-empty lines) ---
SOFT_LIMIT = 150  # Target: where we want to be
HARD_LIMIT = 200  # Absolute max before CI fails

# --- Configuration: characters per physical line (align with Ruff) ---
MAX_LINE_CHAR_LIMIT = 79

# Directories relative to project root to scan
SCAN_DIRECTORIES = ["src", "tests"]


def _count_lines(file_path: Path) -> int:
    """Count non-empty lines in a file (more meaningful than raw line"""
    """count)."""
    try:
        with open(file_path, encoding="utf-8") as f:
            # Count lines that have at least one non-whitespace character
            return sum(1 for line in f if line.strip())
    except (OSError, UnicodeDecodeError) as e:
        pytest.fail(f"Unreadable file {file_path}: {e}")


def test_python_files_respect_line_count_limits():
    """
    Ensure no Python file exceeds HARD_LIMIT non-empty lines.

    Files exceeding the soft limit indicate:
    - Too many responsibilities in a single module
    - Need for refactoring into smaller, focused modules
    - Potential violation of the Single Responsibility Principle

    The hard limit is a safety rail against runaway files; prefer staying near
    the soft limit by splitting modules when touching them.
    """
    project_root = Path(__file__).resolve().parent.parent
    violations = []
    scanned = 0

    for directory in SCAN_DIRECTORIES:
        dir_path = project_root / directory
        if not dir_path.exists():
            pytest.fail(f"Directory '{directory}' not found at {dir_path}")

        for py_file in dir_path.rglob("*.py"):
            scanned += 1
            line_count = _count_lines(py_file)

            if line_count > HARD_LIMIT:
                relative = py_file.relative_to(project_root)
                over_by = line_count - SOFT_LIMIT
                violations.append(
                    {
                        "path": str(relative),
                        "lines": line_count,
                        "over_soft_limit": max(0, over_by),
                        "over_hard_limit": line_count - HARD_LIMIT,
                    }
                )

    # --- Reporting ---
    if violations:
        # Sort by severity (most over limit first)
        violations.sort(key=lambda v: v["lines"], reverse=True)

        lines = [
            f"\n{'=' * 60}",
            "PYTHON FILE LENGTH VIOLATIONS",
            f"{'=' * 60}",
            f"Scanned: {scanned} files",
            f"Soft limit: {SOFT_LIMIT} | Hard limit: {HARD_LIMIT}",
            f"{'-' * 60}",
        ]

        for v in violations:
            marker = " 🔴 HARD" if v["over_hard_limit"] > 0 else " 🟡 SOFT"
            lines.append(
                f"{v['path']}: {v['lines']} lines "
                f"({v['over_soft_limit']} over soft limit){marker}"
            )

        lines.extend(
            [
                f"{'-' * 60}",
                "Refactoring suggestions:",
                "  • Extract classes/functions into dedicated modules",
                "  • Split large test files by feature or domain",
                "  • Move configuration/data tables to separate "
                "constants files",
                "  • Consider the 'Composition over Inheritance' principle",
                f"{'=' * 60}",
            ]
        )

        pytest.fail("\n".join(lines))

    # Always print a summary so the test feels substantive even when passing
    print(f"\n✅ File-length check passed: {scanned} files scanned.")


def _scan_line_width_violations(
    project_root: Path, max_chars: int
) -> tuple[list[str], int]:
    """Return (messages, scanned). Each message is one over-long line."""
    messages: list[str] = []
    scanned = 0

    for directory in SCAN_DIRECTORIES:
        dir_path = project_root / directory
        if not dir_path.exists():
            pytest.fail(f"Directory '{directory}' not found at {dir_path}")

        for py_file in dir_path.rglob("*.py"):
            scanned += 1
            try:
                text = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                pytest.fail(f"Unreadable file {py_file}: {e}")

            relative = py_file.relative_to(project_root)
            for lineno, line in enumerate(text.splitlines(), start=1):
                n = len(line)
                if n > max_chars:
                    messages.append(
                        f"{relative}:{lineno}: {n} chars (max {max_chars})"
                    )

    return messages, scanned


def test_python_source_line_width_max_79_chars():
    """No physical line may exceed MAX_LINE_CHAR_LIMIT (kept in sync with"""
    """Ruff)."""
    project_root = Path(__file__).resolve().parent.parent
    violations, scanned = _scan_line_width_violations(
        project_root, MAX_LINE_CHAR_LIMIT
    )

    if violations:
        head = [
            f"\n{'=' * 60}",
            "PYTHON LINE WIDTH VIOLATIONS",
            f"(max {MAX_LINE_CHAR_LIMIT} chars/line; see "
            f"pyproject.toml [tool.ruff])",
            f"{'=' * 60}",
            f"Scanned: {scanned} files",
            f"{'-' * 60}",
        ]
        violations.sort()
        pytest.fail("\n".join(head + violations + [f"{'=' * 60}"]))

    print(
        f"\n✅ Line-width check passed: {scanned} files scanned "
        f"(max {MAX_LINE_CHAR_LIMIT} chars/line)."
    )
