"""Logging formatters and filters."""

from __future__ import annotations

import itertools
import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_EVENT_COUNTER = itertools.count(1)


@dataclass(frozen=True)
class PrefixFilter:
    """Pass records whose logger name starts with any of the given prefixes."""

    prefixes: tuple[str, ...]

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name.startswith(p) for p in self.prefixes)


@dataclass(frozen=True)
class A2aSdkFilter:
    """Third-party A2A SDK loggers (exclude our ``a2a_research`` package)."""

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        if name.startswith("a2a_research"):
            return False
        return name == "a2a" or name.startswith("a2a.")


@dataclass(frozen=True)
class HttpClientsFilter:
    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        if name == "httpcore" or name.startswith("httpcore."):
            return True
        return name == "httpx" or name.startswith("httpx.")


@dataclass(frozen=True)
class MesopServerFilter:
    _roots: frozenset[str] = frozenset(
        {"mesop", "flask", "werkzeug", "uvicorn"}
    )

    def filter(self, record: logging.LogRecord) -> bool:
        base = record.name.split(".", 1)[0]
        return base in self._roots


@dataclass(frozen=True)
class WarningsFilter:
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name == "py.warnings"


def _normalize_log_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(key): _normalize_log_value(val) for key, val in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_normalize_log_value(item) for item in value]
    if hasattr(value, "value"):
        return _normalize_log_value(value.value)
    if hasattr(value, "model_dump"):
        return _normalize_log_value(value.model_dump())
    if hasattr(value, "__dict__"):
        return _normalize_log_value(vars(value))
    return repr(value)


def log_event(
    logger: logging.Logger, level: int, event: str, **fields: Any
) -> None:
    """Write a granular structured log line (``event=`` + JSON payload)."""
    payload = {
        "seq": next(_EVENT_COUNTER),
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        "pid": os.getpid(),
        "thread": threading.current_thread().name,
        **{key: _normalize_log_value(value) for key, value in fields.items()},
    }
    logger.log(
        level,
        "event=%s payload=%s",
        event,
        json.dumps(payload, sort_keys=True),
    )


def build_formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] pid=%(process)d "
        "tid=%(thread)d %(message)s"
    )


__all__ = [
    "A2aSdkFilter",
    "HttpClientsFilter",
    "MesopServerFilter",
    "PrefixFilter",
    "WarningsFilter",
    "build_formatter",
    "log_event",
]
