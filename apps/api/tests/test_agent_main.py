"""Tests for agent __main__.py entry points."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from a2a_research.backend.agents.langgraph.fact_checker.__main__ import (
    main as fact_checker_main,
)
from a2a_research.backend.agents.pocketflow.clarifier.__main__ import (
    main as clarifier_main,
)
from a2a_research.backend.agents.pocketflow.planner.__main__ import (
    main as planner_main,
)
from a2a_research.backend.agents.pydantic_ai.synthesizer.__main__ import (
    main as synthesizer_main,
)
from a2a_research.backend.agents.smolagents.reader.__main__ import (
    main as reader_main,
)
from a2a_research.backend.agents.smolagents.searcher.__main__ import (
    main as searcher_main,
)


@pytest.mark.parametrize(
    "main_func, expected_module, port_attr",
    [
        (
            fact_checker_main,
            "a2a_research.backend.agents.langgraph"
            ".fact_checker.main:build_http_app",
            "fact_checker_port",
        ),
        (
            clarifier_main,
            "a2a_research.backend.agents.pocketflow"
            ".clarifier.main:build_http_app",
            "clarifier_port",
        ),
        (
            planner_main,
            "a2a_research.backend.agents.pocketflow"
            ".planner.main:build_http_app",
            "planner_port",
        ),
        (
            synthesizer_main,
            "a2a_research.backend.agents.pydantic_ai"
            ".synthesizer.main:build_http_app",
            "synthesizer_port",
        ),
        (
            reader_main,
            "a2a_research.backend.agents.smolagents"
            ".reader.main:build_http_app",
            "reader_port",
        ),
        (
            searcher_main,
            "a2a_research.backend.agents.smolagents"
            ".searcher.main:build_http_app",
            "searcher_port",
        ),
    ],
)
def test_agent_main_calls_uvicorn(
    main_func: object,
    expected_module: str,
    port_attr: str,
) -> None:
    """Verify each agent __main__.main() calls uvicorn.run."""
    mock_settings = MagicMock()
    setattr(mock_settings, port_attr, 9999)

    with (
        patch("uvicorn.run") as mock_run,
        patch(
            "a2a_research.backend.agents.langgraph"
            ".fact_checker.__main__.settings",
            mock_settings,
        ),
        patch(
            "a2a_research.backend.agents.pocketflow"
            ".clarifier.__main__.settings",
            mock_settings,
        ),
        patch(
            "a2a_research.backend.agents.pocketflow.planner.__main__.settings",
            mock_settings,
        ),
        patch(
            "a2a_research.backend.agents.pydantic_ai"
            ".synthesizer.__main__.settings",
            mock_settings,
        ),
        patch(
            "a2a_research.backend.agents.smolagents.reader.__main__.settings",
            mock_settings,
        ),
        patch(
            "a2a_research.backend.agents.smolagents"
            ".searcher.__main__.settings",
            mock_settings,
        ),
    ):
        main_func()
        mock_run.assert_called_once_with(
            expected_module,
            host="0.0.0.0",
            port=9999,
            factory=True,
        )
