"""Start all five HTTP A2A agent services as subprocesses."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

from a2a_research.app_logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    module: str


SERVICES = [
    ServiceSpec("planner", "a2a_research.agents.pocketflow.planner"),
    ServiceSpec("searcher", "a2a_research.agents.smolagents.searcher"),
    ServiceSpec("reader", "a2a_research.agents.smolagents.reader"),
    ServiceSpec("fact-checker", "a2a_research.agents.langgraph.fact_checker"),
    ServiceSpec("synthesizer", "a2a_research.agents.pydantic_ai.synthesizer"),
]


def _stream_logs(name: str, process: subprocess.Popen[str]) -> None:
    if process.stdout is None:
        return
    for line in process.stdout:
        logger.info("[%s] %s", name, line.rstrip())


def main() -> None:
    env = os.environ.copy()
    processes: list[subprocess.Popen[str]] = []
    threads: list[threading.Thread] = []

    try:
        for service in SERVICES:
            process = subprocess.Popen(
                [sys.executable, "-m", service.module],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
            )
            processes.append(process)
            thread = threading.Thread(
                target=_stream_logs, args=(service.name, process), daemon=True
            )
            thread.start()
            threads.append(thread)

        while True:
            for process, service in zip(processes, SERVICES, strict=False):
                code = process.poll()
                if code is not None:
                    raise RuntimeError(
                        f"Service {service.name} exited unexpectedly with code {code}"
                    )
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received SIGINT, stopping services")
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
