.DEFAULT_GOAL := help
.PHONY: help install dev test watch lint format format-check typecheck typecheck-ty check all clean mesop htmlcov

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install package with uv
	uv sync --all-groups

dev: install ## Full dev setup: install + activate pre-commit hooks
	uv run pre-commit install
	@echo "Dev environment ready. Run 'make test' to verify."

test: ## Run pytest suite with coverage
	uv run pytest

watch: ## Run pytest in watch mode (re-runs on file changes)
	uv run pytest --tb=short -q --no-header -p no:warnings -f

lint: ## Run ruff linter
	uv run ruff check src/ tests/

format: ## Format code with ruff
	uv run ruff format src/ tests/

format-check: ## Check formatting without modifying files
	uv run ruff format --check src/ tests/

typecheck: ## Run mypy type checker
	uv run mypy src/

typecheck-ty: ## Run ty type checker
	uv run ty check src/

check: lint typecheck typecheck-ty format-check ## Run all quality checks (no tests)

all: test check ## Run tests + all quality checks (CI-ready)
	@echo "[OK] All checks complete"

clean: ## Remove build artifacts and cache directories
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('**/__pycache__')]"
	python -c "import shutil; [shutil.rmtree(d, ignore_errors=True) for d in ['build', 'dist', '.mypy_cache', '.ruff_cache', '.pytest_cache', 'htmlcov']]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('*.egg-info') if p.is_dir()]"

mesop: ## Start Mesop UI (with MESOP_STATE_SESSION_BACKEND=memory)
	export MESOP_STATE_SESSION_BACKEND=memory && uv run mesop src/a2a_research/ui/app.py

htmlcov: ## Generate HTML coverage report
	uv run pytest --cov=src/a2a_research --cov-report=html
	@echo "HTML coverage report generated in htmlcov/index.html"
