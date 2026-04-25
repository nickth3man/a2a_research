.DEFAULT_GOAL := help
.PHONY: help install dev test watch lint format format-check typecheck typecheck-ty check all clean serve htmlcov serve-all serve-planner serve-searcher serve-reader serve-fact-checker serve-synthesizer serve-clarifier frontend-install frontend-dev frontend-build frontend-lint

	help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install all workspace dependencies (pnpm + uv)
	pnpm install
	cd apps/api && uv sync --all-groups

dev: install ## Full dev setup: install + activate pre-commit hooks
	cd apps/api && uv run pre-commit install
	@echo "Dev environment ready. Run 'make test' to verify."

test: ## Run pytest suite via turbo
	"node_modules/.bin/turbo.cmd" run test

watch: ## Run pytest in watch mode (re-runs on file changes)
	cd apps/api && uv run pytest --tb=short -q --no-header -p no:warnings -f

lint: ## Run linters via turbo (ruff + eslint)
	"node_modules/.bin/turbo.cmd" run lint

format: ## Format Python code with ruff
	cd apps/api && uv run ruff format agents/ core/ entrypoints/ llm/ tools/ workflow/ tests/

format-check: ## Check Python formatting without modifying files
	cd apps/api && uv run ruff format --check agents/ core/ entrypoints/ llm/ tools/ workflow/ tests/

typecheck: ## Run mypy type checker
	cd apps/api && uv run mypy agents/ core/ entrypoints/ llm/ tools/ workflow/

typecheck-ty: ## Run ty type checker
	cd apps/api && uv run ty check agents/ core/ entrypoints/ llm/ tools/ workflow/

check: lint typecheck typecheck-ty format-check ## Run all quality checks (no tests)
all: test check ## Run tests + all quality checks (CI-ready)
	@echo "[OK] All checks complete"

clean: ## Remove build artifacts and cache directories
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('**/__pycache__')]"
	python -c "import shutil; [shutil.rmtree(d, ignore_errors=True) for d in ['build', 'dist', '.mypy_cache', '.ruff_cache', '.pytest_cache', 'htmlcov']]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('*.egg-info') if p.is_dir()]"

serve: ## Start unified backend (FastAPI + all agents on port 8000)
	cd apps/api && uv run uvicorn a2a_research.backend.entrypoints.api:app --host 0.0.0.0 --port 8000 --reload

frontend-install: ## Install frontend dependencies
	pnpm install

frontend-dev: ## Start Vite dev server for the React frontend
	cd apps/web && pnpm run dev

frontend-build: ## Build production frontend bundle
	cd apps/web && pnpm run build

frontend-lint: ## Lint frontend code
	cd apps/web && pnpm run lint

serve-all: ## Start all agent HTTP services on separate ports (standalone dev mode)
	cd apps/api && uv run python -m a2a_research.backend.entrypoints.launcher

serve-planner: ## Start Planner HTTP service
	cd apps/api && uv run python -m a2a_research.backend.agents.pocketflow.planner

serve-searcher: ## Start Searcher HTTP service
	cd apps/api && uv run python -m a2a_research.backend.agents.smolagents.searcher

serve-reader: ## Start Reader HTTP service
	cd apps/api && uv run python -m a2a_research.backend.agents.smolagents.reader

serve-fact-checker: ## Start FactChecker HTTP service
	cd apps/api && uv run python -m a2a_research.backend.agents.langgraph.fact_checker

serve-synthesizer: ## Start Synthesizer HTTP service
	cd apps/api && uv run python -m a2a_research.backend.agents.pydantic_ai.synthesizer

serve-clarifier: ## Start Clarifier HTTP service
	cd apps/api && uv run python -m a2a_research.backend.agents.pocketflow.clarifier

htmlcov: ## Generate HTML coverage report
	cd apps/api && uv run pytest --cov=src/a2a_research --cov-report=html
	@echo "HTML coverage report generated in htmlcov/index.html"
