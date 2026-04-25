"""Run the Searcher as an HTTP A2A service."""

from __future__ import annotations

import uvicorn

from core import settings


def main() -> None:
    uvicorn.run(
        "agents.smolagents.searcher.main:build_http_app",
        host="0.0.0.0",
        port=settings.searcher_port,
        factory=True,
    )


if __name__ == "__main__":
    main()
