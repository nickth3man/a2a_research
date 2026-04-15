.PHONY: help install test lint format typecheck typecheck-ty clean mesop ingest check

help:
	@echo "Available targets:"
	@echo "  install      - Install package with uv"
	@echo "  test         - Run pytest suite with coverage"
	@echo "  lint         - Run ruff linter"
	@echo "  format       - Run ruff formatter"
	@echo "  typecheck    - Run mypy type checker"
	@echo "  typecheck-ty - Run ty type checker"
	@echo "  check        - Run lint, format check, typecheck, and typecheck-ty"
	@echo "  clean        - Remove build artifacts and cache directories"
	@echo "  mesop        - Start the Mesop UI development server"
	@echo "  ingest       - Ingest the RAG corpus into ChromaDB"

install:
	uv pip install -e .

test:
	uv run pytest

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
	uv run mesop src/a2a_research/ui/app.py

ingest:
	uv run python -c "from a2a_research.rag import ingest_corpus; print(f'Ingested {ingest_corpus()} chunks')"
