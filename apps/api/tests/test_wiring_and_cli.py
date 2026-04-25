"""Tests for thin wiring modules (imports, CLI, launcher)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from core import AgentResult, AgentRole, AgentStatus, ResearchSession


def test_core_utils_package_reexports() -> None:
    import core.utils as utils

    assert utils.to_float("2.5", 0.0) == 2.5
    assert utils.to_str_list(["a", 1]) == ["a", "1"]


def test_fact_checker_nodes_exports_verify_claims() -> None:
    from agents.langgraph.fact_checker import nodes

    assert nodes.__all__ == ["verify_claims"]
    assert callable(nodes.verify_claims)


def test_workflow_engine_loop_reexports() -> None:
    import workflow
    import workflow.engine_loop as el

    assert el.run_evidence_loop is workflow.run_evidence_loop


def test_workflow_main_usage_exits_2() -> None:
    import workflow.__main__ as wm

    with patch.object(sys, "argv", ["workflow"]):
        with pytest.raises(SystemExit) as exc:
            wm.main()
    assert exc.value.code == 2


def test_workflow_main_empty_query_exits_2() -> None:
    import workflow.__main__ as wm

    with patch.object(sys, "argv", ["workflow", " ", "\t"]):
        with pytest.raises(SystemExit) as exc:
            wm.main()
    assert exc.value.code == 2


@patch("workflow.__main__.run_research_sync")
def test_workflow_main_success_prints_report(
    m_run: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    import workflow.__main__ as wm

    m_run.return_value = ResearchSession(
        agent_results={
            AgentRole.PLANNER: AgentResult(
                role=AgentRole.PLANNER,
                status=AgentStatus.COMPLETED,
                message="ok",
            )
        },
        final_report="# Title",
    )
    with patch.object(sys, "argv", ["workflow", "hello", "world"]):
        wm.main()
    out, err = capsys.readouterr()
    assert "# Title" in out
    assert "[planner]" in err
    assert "COMPLETED" in err


@patch("workflow.__main__.run_research_sync")
def test_workflow_main_error_path(
    m_run: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    import workflow.__main__ as wm

    m_run.return_value = ResearchSession(
        error="failed", agent_results={}, final_report=""
    )
    with patch.object(sys, "argv", ["workflow", "q"]):
        wm.main()
    _, err = capsys.readouterr()
    assert "failed" in err


def test_launcher_defines_five_services() -> None:
    from entrypoints import launcher

    names = [s.name for s in launcher.SERVICES]
    assert names == [
        "planner",
        "searcher",
        "reader",
        "fact-checker",
        "synthesizer",
    ]
    assert all(s.port > 0 for s in launcher.SERVICES)


@patch("entrypoints.launcher.time.sleep", side_effect=KeyboardInterrupt)
def test_launcher_main_finishes_on_keyboard_interrupt(
    _sleep: MagicMock,
) -> None:
    from entrypoints import launcher

    with patch("entrypoints.launcher.uvicorn.Config"):
        with patch("entrypoints.launcher.uvicorn.Server") as m_srv:
            serv = MagicMock()
            m_srv.return_value = serv
            th = MagicMock()
            th.is_alive.return_value = True
            with patch(
                "entrypoints.launcher.threading.Thread", return_value=th
            ):
                launcher.main()
    assert serv.should_exit is True
    th.join.assert_called()
