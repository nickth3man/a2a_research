"""Run the Synthesizer as an HTTP A2A service."""

from __future__ import annotations

import uvicorn

from a2a_research.settings import settings


def main() -> None:
    uvicorn.run(
        "a2a_research.agents.pydantic_ai.synthesizer.main:build_http_app",
        host="0.0.0.0",
        port=settings.synthesizer_port,
        factory=True,
    )


if __name__ == "__main__":
    main()
