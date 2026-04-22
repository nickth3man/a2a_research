"""Tests for a2a_research.agents.langgraph.fact_checker module exports."""

from __future__ import annotations


class TestFactCheckerExports:
    def test_fact_checker_executor_importable(self) -> None:
        from a2a_research.backend.agents.langgraph.fact_checker import (
            FactCheckerExecutor,
        )

        assert FactCheckerExecutor is not None

    def test_run_fact_check_importable(self) -> None:
        from a2a_research.backend.agents.langgraph.fact_checker import (
            run_fact_check,
        )

        assert callable(run_fact_check)

    def test_fact_check_state_importable(self) -> None:
        from a2a_research.backend.agents.langgraph.fact_checker import (
            FactCheckState,
        )

        assert FactCheckState is not None

    def test_fact_checker_executor_is_agent_executor(self) -> None:
        from a2a.server.agent_execution import AgentExecutor

        from a2a_research.backend.agents.langgraph.fact_checker import (
            FactCheckerExecutor,
        )

        assert issubclass(FactCheckerExecutor, AgentExecutor)

    def test_all_exports_in_all(self) -> None:
        import a2a_research.backend.agents.langgraph.fact_checker as fc_module

        assert "FactCheckerExecutor" in fc_module.__all__
        assert "run_fact_check" in fc_module.__all__
        assert "FactCheckState" in fc_module.__all__
