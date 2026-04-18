"""Run the FactChecker as an HTTP A2A service."""

from __future__ import annotations

import uvicorn

from a2a_research.settings import settings


def main() -> None:
    uvicorn.run(
        "a2a_research.agents.langgraph.fact_checker.main:build_http_app",
        host="0.0.0.0",
        port=settings.fact_checker_port,
        factory=True,
    )


if __name__ == "__main__":
    main()
