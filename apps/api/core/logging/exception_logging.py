"""Exception-hook helpers for structured logging."""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from typing import Any


def install_exception_hooks() -> None:
    """Install exception hooks that log and preserve original handlers."""
    original_thread_excepthook = threading.excepthook

    def _log_unhandled_exception(
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: Any,
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


def install_asyncio_exception_logging(
    loop: asyncio.AbstractEventLoop | None = None,
) -> None:
    """Attach an exception handler that records background task failures."""
    from core import setup_logging

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
        exc_info: BaseException | None = (
            exc_raw if isinstance(exc_raw, BaseException) else None
        )
        logging.getLogger("a2a_research.asyncio").error(
            "Asyncio exception: %s",
            context.get("message", "no message"),
            extra={"context_keys": sorted(context.keys())},
            exc_info=exc_info,
        )
        default_handler = loop.default_exception_handler
        default_handler(context)

    target_loop.set_exception_handler(_handle_async_exception)
