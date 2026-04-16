"""Compatibility export for the UI ``AppState``.

The runtime-safe state class now lives in :mod:`a2a_research.ui.app` so Mesop
registers and reads the same class object during page rendering.
"""

from a2a_research.ui.app import AppState

__all__ = ["AppState"]
