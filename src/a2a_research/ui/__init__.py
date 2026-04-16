"""Mesop web UI for the research pipeline.

Run (recommended from repo root)::

    make mesop

That sets ``MESOP_STATE_SESSION_BACKEND=memory`` so Mesop keeps UI state server-side
and avoids common dev-console state diff issues after hot reload.

Alternative::

    uv run mesop src/a2a_research/ui/app.py

Environment (see ``.env.example``): ``MESOP_PORT``, and optionally ``MESOP_STATE_SESSION_BACKEND`` (``none`` | ``memory`` | ``file``, etc.). The UI
reads ``ResearchSession`` from ``AppState`` (always present; ``default_factory``)
so Mesop's Pydantic state cache stays consistent.

Submodules: ``app`` (page + handlers), ``components`` (presentational Mesop widgets),
``session_state`` / ``theme`` (pure Python helpers).
"""

from a2a_research.ui import app, components

__all__ = ["app", "components"]
