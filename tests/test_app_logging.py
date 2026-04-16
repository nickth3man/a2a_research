from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import a2a_research.app_logging as logging_module
from a2a_research.app_logging import get_logger, log_event, setup_logging
from a2a_research.models import AgentRole, AgentStatus

if TYPE_CHECKING:
    import pytest


class TestNormalizeLogValue:
    def test_primitive_types_passthrough(self) -> None:
        normalize = logging_module._normalize_log_value
        assert normalize("hello") == "hello"
        assert normalize(42) == 42
        assert normalize(3.14) == 3.14
        assert normalize(True) is True
        assert normalize(None) is None

    def test_path_converted_to_string(self) -> None:
        normalize = logging_module._normalize_log_value
        assert normalize(Path("/tmp/foo")) == str(Path("/tmp/foo"))

    def test_dict_recursively_normalizes(self) -> None:
        normalize = logging_module._normalize_log_value
        assert normalize({"role": AgentRole.RESEARCHER}) == {"role": "researcher"}

    def test_list_recursively_normalizes(self) -> None:
        normalize = logging_module._normalize_log_value
        assert normalize([Path("/tmp"), AgentStatus.COMPLETED]) == [
            str(Path("/tmp")),
            "COMPLETED",
        ]

    def test_pydantic_model_dumped(self) -> None:
        normalize = logging_module._normalize_log_value
        result = normalize(AgentRole.ANALYST)
        assert result == "analyst"

    def test_object_with_attributes_is_normalized_via___dict__(self) -> None:
        class Foo:
            def __init__(self) -> None:
                self.role = AgentRole.RESEARCHER

        normalize = logging_module._normalize_log_value
        assert normalize(Foo()) == {"role": "researcher"}


class TestLogEvent:
    def test_log_event_does_not_raise_on_complex_payload(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        logger = logging.getLogger("test.logger")
        with caplog.at_level(logging.INFO, logger="test.logger"):
            log_event(
                logger,
                logging.INFO,
                "test.event",
                role=AgentRole.RESEARCHER,
                status=AgentStatus.COMPLETED,
                path=Path("/tmp"),
                nested={"items": [1, 2]},
            )

        record = next(r for r in caplog.records if r.name == "test.logger")
        assert "test.event" in record.message
        assert '"role": "researcher"' in record.message


class TestSetupLogging:
    def test_setup_logging_is_idempotent(self, tmp_path: Path) -> None:
        def make_file_handler(*_args: object, **_kwargs: object) -> logging.Handler:
            return logging.StreamHandler(io.StringIO())

        root = logging.getLogger()
        existing_handlers = list(root.handlers)
        for handler in existing_handlers:
            handler.close()
            root.removeHandler(handler)

        with (
            patch("a2a_research.app_logging._LOG_DIR", tmp_path / "logs"),
            patch("a2a_research.app_logging._APP_LOG", tmp_path / "logs" / "app.log"),
            patch("a2a_research.app_logging._ERROR_LOG", tmp_path / "logs" / "errors.log"),
            patch("a2a_research.app_logging._TRACE_LOG", tmp_path / "logs" / "trace.log"),
            patch("a2a_research.app_logging.logging.FileHandler", side_effect=make_file_handler),
        ):
            import a2a_research.app_logging as logging_mod

            original = logging_mod._CONFIGURED
            try:
                logging_mod._CONFIGURED = False
                setup_logging()
                handler_count = len(logging.getLogger().handlers)
                setup_logging()
                assert len(logging.getLogger().handlers) == handler_count
            finally:
                for handler in list(root.handlers):
                    handler.close()
                    root.removeHandler(handler)
                for handler in existing_handlers:
                    root.addHandler(handler)
                logging_mod._CONFIGURED = original

    def test_get_logger_triggers_setup(self, tmp_path: Path) -> None:
        def make_file_handler(*_args: object, **_kwargs: object) -> logging.Handler:
            return logging.StreamHandler(io.StringIO())

        root = logging.getLogger()
        existing_handlers = list(root.handlers)
        for handler in existing_handlers:
            handler.close()
            root.removeHandler(handler)

        with (
            patch("a2a_research.app_logging._LOG_DIR", tmp_path / "logs"),
            patch("a2a_research.app_logging._APP_LOG", tmp_path / "logs" / "app.log"),
            patch("a2a_research.app_logging._ERROR_LOG", tmp_path / "logs" / "errors.log"),
            patch("a2a_research.app_logging._TRACE_LOG", tmp_path / "logs" / "trace.log"),
            patch("a2a_research.app_logging.logging.FileHandler", side_effect=make_file_handler),
        ):
            import a2a_research.app_logging as logging_mod

            original = logging_mod._CONFIGURED
            try:
                logging_mod._CONFIGURED = False
                logger = get_logger("test.module")
                assert isinstance(logger, logging.Logger)
                assert logger.name == "test.module"
            finally:
                for handler in list(root.handlers):
                    handler.close()
                    root.removeHandler(handler)
                for handler in existing_handlers:
                    root.addHandler(handler)
                logging_mod._CONFIGURED = original
