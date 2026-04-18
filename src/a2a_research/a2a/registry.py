"""Role-to-URL registry for HTTP-based A2A services.

Also retains an in-process handler seam for executor-level unit tests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from a2a_research.models import AgentRole
from a2a_research.settings import settings

__all__ = ["AgentRegistry", "get_registry", "reset_registry"]

ExecutorFactory = Callable[[], AgentExecutor]


@dataclass
class AgentRegistry:
    """Resolves agent roles to configured HTTP service URLs."""

    planner_url: str = settings.planner_url
    searcher_url: str = settings.searcher_url
    reader_url: str = settings.reader_url
    fact_checker_url: str = settings.fact_checker_url
    synthesizer_url: str = settings.synthesizer_url

    def __post_init__(self) -> None:
        self._store = InMemoryTaskStore()
        self._factories: dict[AgentRole, ExecutorFactory] = {}
        self._handlers: dict[AgentRole, DefaultRequestHandler] = {}

    def get_url(self, role: AgentRole) -> str:
        mapping = {
            AgentRole.PLANNER: self.planner_url,
            AgentRole.SEARCHER: self.searcher_url,
            AgentRole.READER: self.reader_url,
            AgentRole.FACT_CHECKER: self.fact_checker_url,
            AgentRole.SYNTHESIZER: self.synthesizer_url,
        }
        return mapping[role]

    def register_factory(self, role: AgentRole, factory: ExecutorFactory) -> None:
        self._factories[role] = factory
        self._handlers.pop(role, None)

    def register_executor(self, role: AgentRole, executor: AgentExecutor) -> None:
        self._factories[role] = lambda: executor
        self._handlers.pop(role, None)

    def has_handler(self, role: AgentRole) -> bool:
        return role in self._factories

    def get_handler(self, role: AgentRole) -> DefaultRequestHandler:
        if role not in self._handlers:
            executor = self._factories[role]()
            self._handlers[role] = DefaultRequestHandler(
                agent_executor=executor,
                task_store=self._store,
            )
        return self._handlers[role]


_registry: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def reset_registry() -> None:
    global _registry
    _registry = None
