"""Tests for a2a_research.a2a.registry (AgentRegistry)."""

from __future__ import annotations

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue

from a2a_research.backend.core.a2a.registry import (
    AgentRegistry,
    get_registry,
    reset_registry,
)
from a2a_research.backend.core.models import AgentRole


class _DummyExecutor(AgentExecutor):
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


class TestAgentRegistryGetUrl:
    def test_planner_url_default(self) -> None:
        reg = AgentRegistry()
        url = reg.get_url(AgentRole.PLANNER)
        assert "/agents/planner" in url

    def test_searcher_url_default(self) -> None:
        reg = AgentRegistry()
        assert "/agents/searcher" in reg.get_url(AgentRole.SEARCHER)

    def test_reader_url_default(self) -> None:
        reg = AgentRegistry()
        assert "/agents/reader" in reg.get_url(AgentRole.READER)

    def test_fact_checker_url_default(self) -> None:
        reg = AgentRegistry()
        assert "/agents/fact-checker" in reg.get_url(AgentRole.FACT_CHECKER)

    def test_synthesizer_url_default(self) -> None:
        reg = AgentRegistry()
        assert "/agents/synthesizer" in reg.get_url(AgentRole.SYNTHESIZER)

    def test_custom_planner_url(self) -> None:
        reg = AgentRegistry(planner_url="http://custom:9999")
        assert reg.get_url(AgentRole.PLANNER) == "http://custom:9999/"

    def test_all_roles_have_url(self) -> None:
        reg = AgentRegistry()
        for role in AgentRole:
            url = reg.get_url(role)
            assert url.startswith("http"), (
                f"Role {role} URL does not start with http: {url}"
            )


class TestAgentRegistryHasHandler:
    def test_no_handler_by_default(self) -> None:
        reg = AgentRegistry()
        assert reg.has_handler(AgentRole.PLANNER) is False

    def test_has_handler_after_register_factory(self) -> None:
        reg = AgentRegistry()
        reg.register_factory(AgentRole.PLANNER, _DummyExecutor)
        assert reg.has_handler(AgentRole.PLANNER) is True

    def test_has_handler_after_register_executor(self) -> None:
        reg = AgentRegistry()
        executor = _DummyExecutor()
        reg.register_executor(AgentRole.SEARCHER, executor)
        assert reg.has_handler(AgentRole.SEARCHER) is True

    def test_other_roles_not_affected(self) -> None:
        reg = AgentRegistry()
        reg.register_factory(AgentRole.PLANNER, _DummyExecutor)
        assert reg.has_handler(AgentRole.SEARCHER) is False


class TestAgentRegistryGetHandler:
    def test_get_handler_returns_handler(self) -> None:
        reg = AgentRegistry()
        reg.register_factory(AgentRole.PLANNER, _DummyExecutor)
        handler = reg.get_handler(AgentRole.PLANNER)
        assert handler is not None

    def test_get_handler_cached_on_second_call(self) -> None:
        reg = AgentRegistry()
        reg.register_factory(AgentRole.PLANNER, _DummyExecutor)
        h1 = reg.get_handler(AgentRole.PLANNER)
        h2 = reg.get_handler(AgentRole.PLANNER)
        assert h1 is h2

    def test_get_handler_calls_factory_once(self) -> None:
        call_count = 0

        def factory() -> _DummyExecutor:
            nonlocal call_count
            call_count += 1
            return _DummyExecutor()

        reg = AgentRegistry()
        reg.register_factory(AgentRole.PLANNER, factory)
        reg.get_handler(AgentRole.PLANNER)
        reg.get_handler(AgentRole.PLANNER)
        assert call_count == 1


class TestAgentRegistryRegisterFactory:
    def test_register_factory_clears_existing_handler(self) -> None:
        reg = AgentRegistry()
        reg.register_factory(AgentRole.PLANNER, _DummyExecutor)
        # Prime the handler cache
        reg.get_handler(AgentRole.PLANNER)
        # Re-register with a new factory
        reg.register_factory(AgentRole.PLANNER, _DummyExecutor)
        # Handler should be evicted from cache
        assert AgentRole.PLANNER not in reg._handlers


class TestAgentRegistryRegisterExecutor:
    def test_executor_wraps_as_factory(self) -> None:
        reg = AgentRegistry()
        executor = _DummyExecutor()
        reg.register_executor(AgentRole.READER, executor)
        assert reg.has_handler(AgentRole.READER) is True

    def test_register_executor_clears_cached_handler(self) -> None:
        reg = AgentRegistry()
        reg.register_factory(AgentRole.READER, _DummyExecutor)
        reg.get_handler(AgentRole.READER)
        executor = _DummyExecutor()
        reg.register_executor(AgentRole.READER, executor)
        assert AgentRole.READER not in reg._handlers


class TestGetRegistrySingleton:
    def test_get_registry_returns_same_instance(self) -> None:
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_reset_registry_creates_fresh_instance(self) -> None:
        r1 = get_registry()
        reset_registry()
        r2 = get_registry()
        assert r1 is not r2

    def test_get_registry_returns_agent_registry(self) -> None:
        reg = get_registry()
        assert isinstance(reg, AgentRegistry)
