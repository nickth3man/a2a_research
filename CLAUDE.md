# OpenCode Agent Instructions

## Developer Commands

Always use `make` for developer commands in this repository. The Makefile is the source of truth for build, test, lint, and serve workflows.

```bash
# Core workflows
make test        # Run pytest suite (excludes live API integration tests)
make test-live-brave   # Run Brave live API tests (requires BRAVE_LIVE=1 + real BRAVE_API_KEY)
make test-live-tavily  # Run Tavily live API tests (requires TAVILY_LIVE=1 + real keys)
make test-live         # Run all live API tests
make lint        # Run ruff linter and auto-fix issues
make format      # Format code with ruff
make check       # Run all quality checks (no tests)
make all         # Run tests + all quality checks (CI-ready, no live tests)
make all-live    # Run live tests + all quality checks (requires API keys)
make watch       # Run pytest in watch mode

# Type checking
make typecheck     # Run mypy type checker
make typecheck-ty  # Run ty type checker

# Setup
make install     # Install package with uv
make dev         # Full dev setup (install + pre-commit hooks)

# Application services
make mesop                  # Start Mesop UI
make serve-all              # Start all agent HTTP services
make serve-planner          # Start Planner HTTP service
make serve-searcher         # Start Searcher HTTP service
make serve-reader           # Start Reader HTTP service
make serve-fact-checker     # Start FactChecker HTTP service
make serve-synthesizer      # Start Synthesizer HTTP service

# Utilities
make clean       # Remove build artifacts and cache directories
make htmlcov     # Generate HTML coverage report
```

> **Note:**
> - *Do not use `glob` or `grep` tools.*
> - *Use the `rg` (ripgrep) or `tree` bash commands for searches, or read files in full.*