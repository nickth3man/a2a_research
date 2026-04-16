.PHONY: help install dev test watch lint format typecheck typecheck-ty clean mesop ingest check

help:
	@echo "Available targets:"
	@echo "  install      - Install package with uv"
	@echo "  dev          - Full dev setup: install package + activate pre-commit hooks"
	@echo "  test         - Run pytest suite with coverage"
	@echo "  watch        - Run pytest in watch mode (re-runs on file changes)"
	@echo "  lint         - Run ruff linter"
	@echo "  format       - Run ruff formatter"
	@echo "  typecheck    - Run mypy type checker"
	@echo "  typecheck-ty - Run ty type checker"
	@echo "  check        - Run lint, format check, typecheck, and typecheck-ty"
	@echo "  clean        - Remove build artifacts and cache directories"
	@echo "  mesop        - Start Mesop UI (MESOP_STATE_SESSION_BACKEND=memory for stable dev state sync)"
	@echo "  ingest       - Ingest the RAG corpus into ChromaDB"

install:
	uv sync --all-groups

dev: install
	uv run pre-commit install
	@echo "Dev environment ready. Run 'make test' to verify."

test:
	uv run pytest

watch:
	uv run pytest --tb=short -q --no-header -p no:warnings -f

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

typecheck-ty:
	uv run ty check src/

check: lint typecheck typecheck-ty
	@echo "Running format check..."
	uv run ruff format --check src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info .mypy_cache .ruff_cache .pytest_cache src/a2a_research/__pycache__ src/a2a_research/*/__pycache__ tests/__pycache__

mesop:
	MESOP_STATE_SESSION_BACKEND=memory uv run mesop src/a2a_research/ui/app.py

ingest:
	uv run python -c "from a2a_research.rag import ingest_corpus; print(f'Ingested {ingest_corpus()} chunks')"
