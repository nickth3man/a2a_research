# scripts

Utility scripts for development, refactoring, and maintenance tasks.

## Files

| File                  | Purpose                                                                              | Inputs                                                                           | Outputs                                                                           | When to run                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `extract_prompts.py`    | Extracts long prompt strings from Python files and externalizes them into `.txt` files | Python files under `src/` and `tests/` with prompt assignments                       | Rewrites matching Python files and writes companion `*_NAME.txt` files next to them | When prompt text is too large to keep inline and you want to externalize it during maintenance |
| `extract_prompts_v2.py` | AST-based prompt extraction utility with broader Python-file coverage                | Python files under `src/` and `tests/`                                               | Rewrites matching Python files and writes companion `*_NAME.txt` files next to them | When performing a more reliable bulk prompt extraction/refactor                                |
| `migrate_imports.py`    | Rewrites imports after the frontend/backend split                                    | `.py` files passed as arguments, or all `.py` files under `src/` and `tests/` by default | Rewrites files in place with updated import paths                                 | When legacy `a2a_research.*` imports need to be migrated to the new backend package layout       |

## Usage

Run these scripts manually during development or maintenance. They are not part of the normal application runtime.

```bash
# Extract prompts using the original line-based extractor
uv run python scripts/extract_prompts.py

# Extract prompts using the AST-based extractor
uv run python scripts/extract_prompts_v2.py

# Rewrite imports across the codebase
uv run python scripts/migrate_imports.py

# Rewrite imports for specific paths only
uv run python scripts/migrate_imports.py src tests
```

## Integration with make

These scripts are standalone and do not appear to have dedicated `make` targets in the repository. Use `uv run python ...` directly unless a workflow is added later.

## Notes

- `extract_prompts.py` and `extract_prompts_v2.py` both write companion `.txt` files next to the source file they process.
- `migrate_imports.py` is idempotent, so running it multiple times should not change already-migrated files.
- These scripts modify files in place, so commit or back up changes before running them on a large set of files.
- Their main operational relevance is refactoring and content extraction, not runtime serving.
