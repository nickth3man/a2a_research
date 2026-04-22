"""Stream redirect utilities for logging."""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    import logging


class StreamToLogger:
    """Mirror writes into the logging system while preserving terminal"""

    """output."""

    def __init__(
        self, logger: logging.Logger, level: int, original_stream: TextIO
    ) -> None:
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


__all__ = ["StreamToLogger"]
