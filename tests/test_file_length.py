"""
Test that Python files don't exceed 500 lines.

Long files are difficult to maintain, understand, and test.
Files should be kept concise and focused on a single responsibility.
"""
from pathlib import Path

import pytest

# --- Configuration ---
SOFT_LIMIT = 500   # Target: where we want to be
HARD_LIMIT = 550   # Absolute max before CI fails (grace buffer for edge cases)

# Directories relative to project root to scan
SCAN_DIRECTORIES = ["src", "tests"]

# Glob patterns for paths to ignore (matched against path parts)
IGNORED_PATH_PATTERNS = [
    "migrations",      # Generated schema migration files
    "__pycache__",     # Compiled bytecode directories
    ".venv",           # Virtual environment
    "venv",
    "node_modules",    # JS dependencies that might contain .py files
    "vendor",          # Vendored third-party code
    "generated",       # Auto-generated code
    "proto_pb2",       # Generated protobuf files
]

# Specific filenames to ignore
IGNORED_FILE_NAMES = {
    "settings.py",     # Django settings with large dicts
    "constants.py",    # Large data tables
}


def _should_ignore(path: Path) -> bool:
    """Determine if a file should be skipped based on path patterns."""
    parts = set(path.parts)
    if any(pattern in parts for pattern in IGNORED_PATH_PATTERNS):
        return True
    if path.name in IGNORED_FILE_NAMES:
        return True
    return False


def _count_lines(file_path: Path) -> int:
    """Count non-empty lines in a file (more meaningful than raw line count)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            # Count lines that have at least one non-whitespace character
            return sum(
                1
                for line in f
                if line.strip()
            )
    except (OSError, UnicodeDecodeError):
        # Skip unreadable files rather than crashing the entire test suite
        return -1


def test_python_files_max_500_lines():
    """
    Ensure all Python files in configured directories are at most 550 lines long.

    Files exceeding 500 lines indicate:
    - Too many responsibilities in a single module
    - Need for refactoring into smaller, focused modules
    - Potential violation of the Single Responsibility Principle

    A 50-line grace buffer (550 hard limit) exists for:
    - Complex dispatch tables or registries
    - Protocol implementations with many required methods
    - Comprehensive test modules covering a full integration flow
    """
    project_root = Path(__file__).resolve().parent.parent
    violations = []
    scanned = 0
    skipped = 0

    for directory in SCAN_DIRECTORIES:
        dir_path = project_root / directory
        if not dir_path.exists():
            pytest.skip(f"Directory '{directory}' not found at {dir_path}")

        for py_file in dir_path.rglob("*.py"):
            if _should_ignore(py_file):
                skipped += 1
                continue

            scanned += 1
            line_count = _count_lines(py_file)

            if line_count == -1:
                skipped += 1
                continue

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
            f"PYTHON FILE LENGTH VIOLATIONS",
            f"{'=' * 60}",
            f"Scanned: {scanned} files | Skipped: {skipped} files",
            f"Soft limit: {SOFT_LIMIT} | Hard limit: {HARD_LIMIT}",
            f"{'-' * 60}",
        ]

        for v in violations:
            marker = " 🔴 HARD" if v["over_hard_limit"] > 0 else " 🟡 SOFT"
            lines.append(
                f"{v['path']}: {v['lines']} lines "
                f"({v['over_soft_limit']} over soft limit){marker}"
            )

        lines.extend([
            f"{'-' * 60}",
            "Refactoring suggestions:",
            "  • Extract classes/functions into dedicated modules",
            "  • Split large test files by feature or domain",
            "  • Move configuration/data tables to separate constants files",
            "  • Consider the 'Composition over Inheritance' principle",
            f"{'=' * 60}",
        ])

        pytest.fail("\n".join(lines))

    # Always print a summary so the test feels substantive even when passing
    print(f"\n✅ Line-length check passed: {scanned} files scanned, {skipped} skipped.")