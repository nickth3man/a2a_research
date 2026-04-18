"""Start all five HTTP A2A agent services in one process."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import uvicorn

from a2a_research.agents.langgraph.fact_checker.main import (
    build_http_app as build_fact_checker_app,
)
from a2a_research.agents.pocketflow.planner.main import build_http_app as build_planner_app
from a2a_research.agents.pydantic_ai.synthesizer.main import (
    build_http_app as build_synthesizer_app,
)
from a2a_research.agents.smolagents.reader.main import build_http_app as build_reader_app
from a2a_research.agents.smolagents.searcher.main import build_http_app as build_searcher_app
from a2a_research.app_logging import get_logger
from a2a_research.settings import settings

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    port: int
    app_factory: Callable[[], Any]


SERVICES = [
    ServiceSpec("planner", settings.planner_port, build_planner_app),
    ServiceSpec("searcher", settings.searcher_port, build_searcher_app),
    ServiceSpec("reader", settings.reader_port, build_reader_app),
    ServiceSpec("fact-checker", settings.fact_checker_port, build_fact_checker_app),
    ServiceSpec("synthesizer", settings.synthesizer_port, build_synthesizer_app),
]


def _run_server(server: uvicorn.Server) -> None:
    server.run()


def main() -> None:
    threads: list[threading.Thread] = []
    servers: list[uvicorn.Server] = []

    try:
        for service in SERVICES:
            config = uvicorn.Config(
                app=service.app_factory(),
                host="0.0.0.0",
                port=service.port,
                log_level="info",
            )
            server = uvicorn.Server(config)
            thread = threading.Thread(target=_run_server, args=(server,), daemon=True)
            thread.start()
            threads.append(thread)
            servers.append(server)
            logger.info("Started %s on port %s", service.name, service.port)

        while True:
            for service, thread in zip(SERVICES, threads, strict=False):
                if not thread.is_alive():
                    raise RuntimeError(f"Service {service.name} stopped unexpectedly")
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received SIGINT, stopping services")
    finally:
        for server in servers:
            server.should_exit = True
        for thread in threads:
            thread.join(timeout=5)


if __name__ == "__main__":
    main()
