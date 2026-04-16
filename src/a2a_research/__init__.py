"""A2A Research — local-first multi-agent research system.

Pipeline (PocketFlow ``AsyncFlow``): Researcher → Analyst → Verifier → Presenter.
Agents talk through an in-process A2A-shaped layer; RAG uses ChromaDB over
``data/corpus``.

Typical entrypoints:

- ``a2a_research.agents.pocketflow.run_research_sync`` — run the full pipeline on a query string.
- ``a2a_research.ui.app`` — Mesop web UI (see ``a2a_research.ui`` package docstring).
- ``a2a_research.rag.ingest_corpus`` / ``retrieve_chunks`` — build and query the vector index.

Configuration is environment-driven; see ``a2a_research.settings`` and the repo ``.env.example``.
"""

__version__ = "0.1.0"
