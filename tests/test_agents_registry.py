from __future__ import annotations

from a2a_research.agents.pocketflow.utils.registry import (
    AgentRegistry,
    AgentSpec,
    get_agent_handler,
    get_agent_spec,
    get_registry,
    register_agent,
)
from a2a_research.models import AgentRole


class TestAgentRegistry:
    def test_register_and_retrieve_spec(self) -> None:
        registry = AgentRegistry()

        def handler(session: object, message: object) -> str:
            return "ok"

        spec = AgentSpec(
            role=AgentRole.RESEARCHER,
            name="Researcher",
            description="Finds docs",
            handler=handler,
        )
        registry.register(spec)

        assert registry.get_spec(AgentRole.RESEARCHER) is spec
        assert registry.get_handler(AgentRole.RESEARCHER) is handler
        assert AgentRole.RESEARCHER in registry

    def test_get_spec_missing_returns_none(self) -> None:
        registry = AgentRegistry()
        assert registry.get_spec(AgentRole.ANALYST) is None
        assert registry.get_handler(AgentRole.ANALYST) is None
        assert AgentRole.ANALYST not in registry

    def test_get_all_roles(self) -> None:
        registry = AgentRegistry()
        registry.register(AgentSpec(role=AgentRole.ANALYST, name="A", description="D"))
        registry.register(AgentSpec(role=AgentRole.VERIFIER, name="V", description="D"))
        assert registry.get_all_roles() == [AgentRole.ANALYST, AgentRole.VERIFIER]

    def test_to_card_copies_fields(self) -> None:
        spec = AgentSpec(
            role=AgentRole.PRESENTER,
            name="Presenter",
            description="Presents",
            version="2.0.0",
            skills=["markdown"],
            input_schema={"x": "str"},
            output_schema={"y": "str"},
        )
        card = spec.to_card()
        assert card.name == "Presenter"
        assert card.role == AgentRole.PRESENTER
        assert card.description == "Presents"
        assert card.version == "2.0.0"
        assert card.skills == ["markdown"]
        assert card.input_schema == {"x": "str"}
        assert card.output_schema == {"y": "str"}


class TestRegisterAgentDecorator:
    def test_decorator_registers_handler(self) -> None:
        registry = get_registry()
        # Save original state to restore after test
        original_spec = registry.get_spec(AgentRole.ANALYST)
        original_card = registry._cards.get(AgentRole.ANALYST)

        try:

            @register_agent(
                AgentRole.ANALYST,
                name="Test Analyst",
                description="Testing",
                version="1.1.0",
                skills=["test"],
            )
            def my_analyst(_session: object, _message: object) -> str:
                return "analyzed"

            spec = get_agent_spec(AgentRole.ANALYST)
            assert spec is not None
            assert spec.name == "Test Analyst"
            assert spec.description == "Testing"
            assert spec.version == "1.1.0"
            assert spec.skills == ["test"]
            assert get_agent_handler(AgentRole.ANALYST) is my_analyst
        finally:
            # Restore original state to prevent leakage to other tests
            if original_spec is not None:
                registry._specs[AgentRole.ANALYST] = original_spec
                registry._cards[AgentRole.ANALYST] = original_card
            else:
                registry._specs.pop(AgentRole.ANALYST, None)
                registry._cards.pop(AgentRole.ANALYST, None)
