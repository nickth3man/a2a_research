.DEFAULT_GOAL := help
.PHONY: help install dev test test-live test-live-brave test-live-tavily all-live watch lint format format-check typecheck typecheck-ty check all clean serve htmlcov serve-all serve-planner serve-searcher serve-reader serve-fact-checker serve-synthesizer frontend-install frontend-dev frontend-build frontend-lint

	help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install package with uv
	uv sync --all-groups

dev: install ## Full dev setup: install + activate pre-commit hooks
	uv run pre-commit install
	@echo "Dev environment ready. Run 'make test' to verify."

test: ## Run pytest suite with coverage (excludes live API integration tests)
	uv run pytest -m "not integration"

test-live-brave: ## Run Brave live API tests (requires BRAVE_LIVE=1 + real BRAVE_API_KEY)
	BRAVE_LIVE=1 uv run pytest tests/test_brave_live_smoke.py tests/test_brave_live_queries.py -n0 --no-cov -m integration

test-live-tavily: ## Run Tavily live API tests (requires TAVILY_LIVE=1 + real keys)
	TAVILY_LIVE=1 uv run pytest tests/test_tavily_live.py tests/test_tavily_live_merge.py -n0 --no-cov -m integration

test-live: test-live-brave test-live-tavily ## Run all live API tests

watch: ## Run pytest in watch mode (re-runs on file changes)
	uv run pytest --tb=short -q --no-header -p no:warnings -f

lint: ## Run ruff linter and auto-fix issues
	uv run ruff check --fix src/ tests/

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

all-live: test-live check ## Run live tests + all quality checks
	@echo "[OK] All live checks complete"

clean: ## Remove build artifacts and cache directories
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('**/__pycache__')]"
	python -c "import shutil; [shutil.rmtree(d, ignore_errors=True) for d in ['build', 'dist', '.mypy_cache', '.ruff_cache', '.pytest_cache', 'htmlcov']]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('*.egg-info') if p.is_dir()]"

serve: ## Start unified backend (FastAPI + all agents on port 8000)
	uv run uvicorn a2a_research.backend.entrypoints.api:app --host 0.0.0.0 --port 8000 --reload

frontend-install: ## Install frontend dependencies
	cd frontend && npm install

frontend-dev: ## Start Vite dev server for the React frontend
	cd frontend && npm run dev

frontend-build: ## Build production frontend bundle
	cd frontend && npm run build

frontend-lint: ## Lint frontend code
	cd frontend && npm run lint

serve-all: ## Start all agent HTTP services on separate ports (standalone dev mode)
	uv run python -m a2a_research.backend.entrypoints.launcher

serve-planner: ## Start Planner HTTP service
	uv run python -m a2a_research.backend.agents.pocketflow.planner

serve-searcher: ## Start Searcher HTTP service
	uv run python -m a2a_research.backend.agents.smolagents.searcher

serve-reader: ## Start Reader HTTP service
	uv run python -m a2a_research.backend.agents.smolagents.reader

serve-fact-checker: ## Start FactChecker HTTP service
	uv run python -m a2a_research.backend.agents.langgraph.fact_checker

serve-synthesizer: ## Start Synthesizer HTTP service
	uv run python -m a2a_research.backend.agents.pydantic_ai.synthesizer

htmlcov: ## Generate HTML coverage report
	uv run pytest --cov=src/a2a_research --cov-report=html
	@echo "HTML coverage report generated in htmlcov/index.html"
