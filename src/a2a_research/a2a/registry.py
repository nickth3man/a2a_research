"""In-process registry mapping :class:`AgentRole` to :class:`DefaultRequestHandler`.

All handlers share a single :class:`InMemoryTaskStore` so Task ids are globally
unique across the pipeline. Agent executors are registered lazily by importing
each agent subpackage — this mirrors the ``register_agent(...)`` pattern from
the old pocketflow registry.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from a2a_research.a2a.cards import get_card
from a2a_research.models import AgentRole

if TYPE_CHECKING:
    from a2a.types import AgentCard

__all__ = [
    "AgentRegistry",
    "get_registry",
    "register_executor",
    "register_executor_factory",
    "reset_registry",
]

ExecutorFactory = Callable[[], AgentExecutor]


class AgentRegistry:
    """Maps :class:`AgentRole` → (:class:`AgentExecutor`, :class:`AgentCard`, :class:`DefaultRequestHandler`)."""

    def __init__(self) -> None:
        self._store = InMemoryTaskStore()
        self._factories: dict[AgentRole, ExecutorFactory] = {}
        self._handlers: dict[AgentRole, DefaultRequestHandler] = {}

    @property
    def task_store(self) -> InMemoryTaskStore:
        return self._store

    def register_factory(self, role: AgentRole, factory: ExecutorFactory) -> None:
        self._factories[role] = factory
        self._handlers.pop(role, None)

    def register_executor(self, role: AgentRole, executor: AgentExecutor) -> None:
        self._factories[role] = lambda: executor
        self._handlers.pop(role, None)

    def get_card(self, role: AgentRole) -> AgentCard:
        return get_card(role)

    def get_handler(self, role: AgentRole) -> DefaultRequestHandler:
        if role not in self._handlers:
            factory = self._factories.get(role)
            if factory is None:
                msg = f"No AgentExecutor registered for role {role.value!r}."
                raise KeyError(msg)
            executor = factory()
            self._handlers[role] = DefaultRequestHandler(
                agent_executor=executor, task_store=self._store
            )
        return self._handlers[role]

    def roles(self) -> list[AgentRole]:
        return list(self._factories.keys())

    def clear(self) -> None:
        self._factories.clear()
        self._handlers.clear()
        self._store = InMemoryTaskStore()


_REGISTRY: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    """Return the lazily-built global registry with all five executors registered."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = AgentRegistry()
        _register_defaults(_REGISTRY)
    return _REGISTRY


def register_executor(role: AgentRole, executor: AgentExecutor) -> None:
    get_registry().register_executor(role, executor)


def register_executor_factory(role: AgentRole, factory: ExecutorFactory) -> None:
    get_registry().register_factory(role, factory)


def reset_registry() -> None:
    global _REGISTRY
    _REGISTRY = None


def _register_defaults(registry: AgentRegistry) -> None:
    """Register each default executor independently; skip any that fail to import.

    Partial registration is fine during bootstrap — agents get registered on
    first ``get_handler`` lookup. Skipping unavailable ones keeps unit tests
    for individual layers from breaking when the full agent set is incomplete.
    """
    _try_register(
        registry,
        AgentRole.PLANNER,
        "a2a_research.agents.pocketflow.planner.main",
        "PlannerExecutor",
    )
    _try_register(
        registry,
        AgentRole.SEARCHER,
        "a2a_research.agents.smolagents.searcher.main",
        "SearcherExecutor",
    )
    _try_register(
        registry, AgentRole.READER, "a2a_research.agents.smolagents.reader.main", "ReaderExecutor"
    )
    _try_register(
        registry,
        AgentRole.FACT_CHECKER,
        "a2a_research.agents.langgraph.fact_checker.main",
        "FactCheckerExecutor",
    )
    _try_register(
        registry,
        AgentRole.SYNTHESIZER,
        "a2a_research.agents.pydantic_ai.synthesizer.main",
        "SynthesizerExecutor",
    )


def _try_register(
    registry: AgentRegistry, role: AgentRole, module_path: str, class_name: str
) -> None:
    import importlib
    import logging

    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
    except (ImportError, AttributeError) as exc:
        logging.getLogger(__name__).debug(
            "Skipping default registration for role=%s (%s): %s",
            role.value,
            module_path,
            exc,
        )
        return
    registry.register_factory(role, cls)
