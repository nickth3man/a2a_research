#!/usr/bin/env python3
"""Rewrite a2a_research imports after the frontend/backend split.

Usage:
    python scripts/migrate_imports.py [paths ...]

If no paths are given, rewrites all .py files under src/ and tests/.
Idempotent: running multiple times produces identical output.

Migrations applied:
    a2a_research.models     -> a2a_research.backend.core.models
    a2a_research.logging    -> a2a_research.backend.core.logging
    a2a_research.progress   -> a2a_research.backend.core.progress
    a2a_research.settings   -> a2a_research.backend.core.settings
    a2a_research.utils      -> a2a_research.backend.core.utils
    a2a_research.a2a        -> a2a_research.backend.core.a2a
    a2a_research.agents     -> a2a_research.backend.agents
    a2a_research.workflow   -> a2a_research.backend.workflow
    a2a_research.tools      -> a2a_research.backend.tools
    a2a_research.llm        -> a2a_research.backend.llm
    a2a_research.entrypoints -> a2a_research.backend.entrypoints
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import libcst as cst
from libcst import CSTTransformer

# ── Mapping: old prefix -> new prefix ────────────────────────────────────
IMPORT_MAP: dict[str, str] = {
    "a2a_research.models": "a2a_research.backend.core.models",
    "a2a_research.logging": "a2a_research.backend.core.logging",
    "a2a_research.progress": "a2a_research.backend.core.progress",
    "a2a_research.settings": "a2a_research.backend.core.settings",
    "a2a_research.utils": "a2a_research.backend.core.utils",
    "a2a_research.a2a": "a2a_research.backend.core.a2a",
    "a2a_research.agents": "a2a_research.backend.agents",
    "a2a_research.workflow": "a2a_research.backend.workflow",
    "a2a_research.tools": "a2a_research.backend.tools",
    "a2a_research.llm": "a2a_research.backend.llm",
    "a2a_research.entrypoints": "a2a_research.backend.entrypoints",
}

# Sort by longest prefix first so sub-module paths match before parents.
_SORTED_KEYS = sorted(IMPORT_MAP, key=len, reverse=True)


def _rewrite_module_name(name: str) -> str:
    """Return rewritten module name, or the original if no mapping matches."""
    for old in _SORTED_KEYS:
        if name == old or name.startswith(old + "."):
            return name.replace(old, IMPORT_MAP[old], 1)
    return name


class ImportRewriter(CSTTransformer):
    """LibCST transformer that rewrites import statements."""

    # ── Handle  `from X import Y` ────────────────────────────────────
    def leave_ImportFrom(
        self,
        original_node: cst.ImportFrom,
        updated_node: cst.ImportFrom,
    ) -> cst.ImportFrom:
        if updated_node.module is None:
            return updated_node

        old_name = cst.helpers.get_full_name_for_node(
            updated_node.module,
        )
        if old_name is None:
            return updated_node
        new_name = _rewrite_module_name(old_name)
        if new_name == old_name:
            return updated_node

        return updated_node.with_changes(
            module=cst.parse_expression(new_name),
        )

    # ── Handle  `import X` and `import X as Y` ──────────────────────
    def leave_Import(
        self,
        original_node: cst.Import,
        updated_node: cst.Import,
    ) -> cst.Import:
        new_names: list[cst.ImportAlias] = []
        changed = False

        for alias in updated_node.names:
            old_name = cst.helpers.get_full_name_for_node(
                alias.name,
            )
            if old_name is None:
                new_names.append(alias)
                continue

            new_name = _rewrite_module_name(old_name)
            if new_name != old_name:
                changed = True
                new_names.append(
                    alias.with_changes(
                        name=cst.parse_expression(new_name),
                    ),
                )
            else:
                new_names.append(alias)

        if not changed:
            return updated_node

        return updated_node.with_changes(names=new_names)


def process_file(filepath: Path) -> bool:
    """Rewrite imports in *filepath*. Returns True if file was modified."""
    source = filepath.read_text(encoding="utf-8")
    try:
        tree = cst.parse_module(source)
    except cst.ParserSyntaxError:
        print(f"  SKIP (parse error): {filepath}", file=sys.stderr)
        return False

    new_tree = tree.visit(ImportRewriter())
    new_source = new_tree.code
    if new_source == source:
        return False

    filepath.write_text(new_source, encoding="utf-8")
    return True


def collect_files(paths: list[str]) -> list[Path]:
    """Collect all .py files from the given paths (files or directories)."""
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite a2a_research imports for frontend/backend split.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["src", "tests"],
        help="Files or directories to rewrite (default: src/ tests/).",
    )
    args = parser.parse_args()

    files = collect_files(args.paths)
    if not files:
        print("No Python files found.", file=sys.stderr)
        sys.exit(1)

    modified = 0
    for fp in files:
        if process_file(fp):
            modified += 1
            print(f"  REWRITTEN: {fp}")

    print(f"\nDone. {modified}/{len(files)} file(s) modified.")


if __name__ == "__main__":
    main()
