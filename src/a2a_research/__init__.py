"""A2A Research — multi-agent web research system orchestrated via the
A2A protocol.

Core runtime combines typed settings, agent-to-agent dispatch, and a
FastAPI gateway for the full research pipeline.

Entrypoints:

- :mod:`a2a_research.backend.entrypoints.api` — FastAPI gateway.
- :mod:`a2a_research.backend.entrypoints.launcher` — standalone agent
  launcher.

Configuration is environment-driven; see ``a2a_research.settings`` and
``.env.example``.
"""

__version__ = "0.2.0"
