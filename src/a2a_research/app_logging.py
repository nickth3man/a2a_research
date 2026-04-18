"""Shared logging setup and logger factory.

``setup_logging`` configures the root logger once. The same ``LOG_LEVEL``
applies everywhere: console and every log file. Records are never dropped by
level within the app.

Files under ``logs/``:

- ``everything.log`` — full audit trail (all loggers).
- ``app.log`` — ``a2a_research.*`` only (this package).
- ``a2a_sdk.log`` — third-party ``a2a`` SDK (``a2a.*``, not ``a2a_research``).
- ``http_clients.log`` — ``httpx`` / ``httpcore``.
- ``mesop_server.log`` — Mesop, Flask, Werkzeug, Uvicorn.
- ``stdio.log`` — captured ``stdout`` / ``stderr`` when using  :func:`redirect_stdio_to_logging`.
- ``warnings.log`` — Python :mod:`warnings` (``py.warnings``).
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
import sys
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO, cast

from a2a_research.settings import settings

if TYPE_CHECKING:
    from types import TracebackType

_CONFIGURED = False
_LOG_DIR = Path.cwd() / "logs"
_LOG_EVERYTHING = _LOG_DIR / "everything.log"
_APP_LOG = _LOG_DIR / "app.log"
_LOG_A2A_SDK = _LOG_DIR / "a2a_sdk.log"
_LOG_HTTP_CLIENTS = _LOG_DIR / "http_clients.log"
_LOG_MESOP_SERVER = _LOG_DIR / "mesop_server.log"
_LOG_STDIO = _LOG_DIR / "stdio.log"
_LOG_WARNINGS = _LOG_DIR / "warnings.log"
_ORIGINAL_STDOUT = sys.stdout
_ORIGINAL_STDERR = sys.stderr
_EVENT_COUNTER = itertools.count(1)


@dataclass(frozen=True)
class _PrefixFilter:
    """Pass records whose logger name starts with any of the given prefixes."""

    prefixes: tuple[str, ...]

    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name.startswith(p) for p in self.prefixes)


@dataclass(frozen=True)
class _A2aSdkFilter:
    """Third-party A2A SDK loggers (exclude our ``a2a_research`` package)."""

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        if name.startswith("a2a_research"):
            return False
        return name == "a2a" or name.startswith("a2a.")


@dataclass(frozen=True)
class _HttpClientsFilter:
    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name
        if name == "httpcore" or name.startswith("httpcore."):
            return True
        return name == "httpx" or name.startswith("httpx.")


@dataclass(frozen=True)
class _MesopServerFilter:
    _roots: frozenset[str] = frozenset({"mesop", "flask", "werkzeug", "uvicorn"})

    def filter(self, record: logging.LogRecord) -> bool:
        base = record.name.split(".", 1)[0]
        return base in self._roots


@dataclass(frozen=True)
class _WarningsFilter:
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name == "py.warnings"


class _StreamToLogger:
    """Mirror writes into the logging system while preserving terminal output."""

    def __init__(self, logger: logging.Logger, level: int, original_stream: TextIO) -> None:
        self._logger = logger
        self._level = level
        self._original_stream = original_stream

    def write(self, message: str) -> None:
        self._original_stream.write(message)
        text = message.strip()
        if text:
            self._logger.log(self._level, text)

    def flush(self) -> None:
        self._original_stream.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._original_stream, "isatty", lambda: False)())


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] pid=%(process)d tid=%(thread)d %(message)s"
    )


def _normalize_log_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize_log_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_log_value(item) for item in value]
    if hasattr(value, "value"):
        return _normalize_log_value(value.value)
    if hasattr(value, "model_dump"):
        return _normalize_log_value(value.model_dump())
    if hasattr(value, "__dict__"):
        return _normalize_log_value(vars(value))
    return repr(value)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """Write a granular structured log line (``event=`` + JSON payload)."""
    payload = {
        "seq": next(_EVENT_COUNTER),
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        "pid": os.getpid(),
        "thread": threading.current_thread().name,
        **{key: _normalize_log_value(value) for key, value in fields.items()},
    }
    logger.log(level, "event=%s payload=%s", event, json.dumps(payload, sort_keys=True))


def _configure_named_logger(name: str, level: int, propagate: bool = True) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate
    return logger


def _install_exception_hooks() -> None:
    """Install exception hooks that log and preserve original handlers."""
    original_excepthook = sys.excepthook
    original_thread_excepthook = threading.excepthook

    def _log_unhandled_exception(
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        if (
            exc_type is not None
            and exc_value is not None
            and not issubclass(exc_type, KeyboardInterrupt)
        ):
            logging.getLogger("a2a_research.unhandled").error(
                "Unhandled exception",
                exc_info=(exc_type, exc_value, exc_traceback),
            )
        original_excepthook(
            cast("type[BaseException]", exc_type),
            cast("BaseException", exc_value),
            exc_traceback,
        )

    def _log_thread_exception(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is not None and args.exc_value is not None:
            logging.getLogger("a2a_research.threading").error(
                "Unhandled thread exception in %s",
                getattr(args.thread, "name", "<unknown>"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
        else:
            logging.getLogger("a2a_research.threading").error(
                "Unhandled thread exception in %s (no exception info)",
                getattr(args.thread, "name", "<unknown>"),
            )
        original_thread_excepthook(args)

    sys.excepthook = _log_unhandled_exception
    threading.excepthook = _log_thread_exception


def install_asyncio_exception_logging(loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Attach an exception handler that records background task failures."""
    setup_logging()
    target_loop = loop
    if target_loop is None:
        try:
            target_loop = asyncio.get_running_loop()
        except RuntimeError:
            return

    def _handle_async_exception(
        loop: asyncio.AbstractEventLoop, context: dict[str, object]
    ) -> None:
        exc_raw = context.get("exception")
        exc_info: BaseException | None = exc_raw if isinstance(exc_raw, BaseException) else None
        logging.getLogger("a2a_research.asyncio").error(
            "Asyncio exception: %s",
            context.get("message", "no message"),
            extra={"context_keys": sorted(context.keys())},
            exc_info=exc_info,
        )
        default_handler = loop.default_exception_handler
        default_handler(context)

    target_loop.set_exception_handler(_handle_async_exception)


def _file_handler(path: Path, level: int, formatter: logging.Formatter) -> logging.FileHandler:
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.DEBUG)
    formatter = _build_formatter()

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    everything_handler = _file_handler(_LOG_EVERYTHING, level, formatter)

    app_handler = _file_handler(_APP_LOG, level, formatter)
    app_handler.addFilter(_PrefixFilter(("a2a_research",)))

    a2a_sdk_handler = _file_handler(_LOG_A2A_SDK, level, formatter)
    a2a_sdk_handler.addFilter(_A2aSdkFilter())

    http_handler = _file_handler(_LOG_HTTP_CLIENTS, level, formatter)
    http_handler.addFilter(_HttpClientsFilter())

    mesop_handler = _file_handler(_LOG_MESOP_SERVER, level, formatter)
    mesop_handler.addFilter(_MesopServerFilter())

    warnings_handler = _file_handler(_LOG_WARNINGS, level, formatter)
    warnings_handler.addFilter(_WarningsFilter())

    root.addHandler(console_handler)
    root.addHandler(everything_handler)
    root.addHandler(app_handler)
    root.addHandler(a2a_sdk_handler)
    root.addHandler(http_handler)
    root.addHandler(mesop_handler)
    root.addHandler(warnings_handler)

    logging.captureWarnings(True)
    _configure_named_logger("asyncio", level)
    _configure_named_logger("mesop", level)
    _configure_named_logger("werkzeug", level)
    _configure_named_logger("flask", level)
    # Trafilatura logs ERROR for non-200 HTTP (e.g. 403) and WARNING for empty extraction;
    # outcomes are summarized in ``a2a_research.tools.fetch`` batch events.
    logging.getLogger("trafilatura.downloads").setLevel(logging.CRITICAL)
    logging.getLogger("trafilatura.core").setLevel(logging.ERROR)
    # stdout/stderr loggers: disable propagation to avoid duplicate console output
    # (they write directly to terminal via _StreamToLogger._original_stream)
    stderr_logger = _configure_named_logger("stderr", level, propagate=False)
    stdout_logger = _configure_named_logger("stdout", level, propagate=False)
    stderr_logger.handlers.clear()
    stdout_logger.handlers.clear()
    stdio_handler = _file_handler(_LOG_STDIO, level, formatter)
    for h in (everything_handler, stdio_handler):
        stdout_logger.addHandler(h)
        stderr_logger.addHandler(h)
    _install_exception_hooks()

    log_event(
        logging.getLogger(__name__),
        logging.INFO,
        "logging.configured",
        configured_level=level_name,
        log_files={
            "everything": str(_LOG_EVERYTHING),
            "app": str(_APP_LOG),
            "a2a_sdk": str(_LOG_A2A_SDK),
            "http_clients": str(_LOG_HTTP_CLIENTS),
            "mesop_server": str(_LOG_MESOP_SERVER),
            "stdio": str(_LOG_STDIO),
            "warnings": str(_LOG_WARNINGS),
        },
    )
    _CONFIGURED = True


def redirect_stdio_to_logging() -> None:
    """Opt-in redirection of sys.stdout/stderr to the logging system."""
    setup_logging()
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.DEBUG)
    sys.stdout = _StreamToLogger(logging.getLogger("stdout"), level, _ORIGINAL_STDOUT)
    sys.stderr = _StreamToLogger(logging.getLogger("stderr"), level, _ORIGINAL_STDERR)


__all__ = [
    "get_logger",
    "install_asyncio_exception_logging",
    "log_event",
    "redirect_stdio_to_logging",
    "setup_logging",
]


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
