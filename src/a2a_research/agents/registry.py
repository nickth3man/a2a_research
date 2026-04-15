"""Agent registry with decorator and spec for extensible PocketFlow + A2A runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from a2a_research.models import AgentCard, AgentRole

if TYPE_CHECKING:
    from a2a_research.models import ResearchSession


AgentHandler = Callable[["ResearchSession", Any], Any]


@dataclass
class AgentSpec:
    role: AgentRole
    name: str
    description: str
    version: str = "1.0.0"
    skills: list[str] = field(default_factory=list)
    input_schema: dict[str, str] = field(default_factory=dict)
    output_schema: dict[str, str] = field(default_factory=dict)
    handler: AgentHandler | None = None

    def to_card(self) -> AgentCard:
        return AgentCard(
            name=self.name,
            role=self.role,
            description=self.description,
            version=self.version,
            skills=self.skills,
            input_schema=self.input_schema,
            output_schema=self.output_schema,
        )


class AgentRegistry:
    _specs: dict[AgentRole, AgentSpec]
    _cards: dict[AgentRole, AgentCard]

    def __init__(self) -> None:
        self._specs = {}
        self._cards = {}

    def register(self, spec: AgentSpec) -> None:
        self._specs[spec.role] = spec
        self._cards[spec.role] = spec.to_card()

    def get_spec(self, role: AgentRole) -> AgentSpec | None:
        return self._specs.get(role)

    def get_card(self, role: AgentRole) -> AgentCard | None:
        return self._cards.get(role)

    def get_handler(self, role: AgentRole) -> AgentHandler | None:
        spec = self._specs.get(role)
        return spec.handler if spec else None

    def all_roles(self) -> list[AgentRole]:
        return list(self._specs.keys())

    def __contains__(self, role: AgentRole) -> bool:
        return role in self._specs


_AGENT_REGISTRY = AgentRegistry()


def register_agent(
    role: AgentRole,
    name: str,
    description: str,
    *,
    version: str = "1.0.0",
    skills: list[str] | None = None,
    input_schema: dict[str, str] | None = None,
    output_schema: dict[str, str] | None = None,
) -> Callable[[AgentHandler], AgentHandler]:
    def decorator(fn: AgentHandler) -> AgentHandler:
        spec = AgentSpec(
            role=role,
            name=name,
            description=description,
            version=version,
            skills=skills or [],
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            handler=fn,
        )
        _AGENT_REGISTRY.register(spec)
        return fn

    return decorator


def get_agent_spec(role: AgentRole) -> AgentSpec | None:
    return _AGENT_REGISTRY.get_spec(role)


def get_agent_handler(role: AgentRole) -> AgentHandler | None:
    return _AGENT_REGISTRY.get_handler(role)


def get_registry() -> AgentRegistry:
    return _AGENT_REGISTRY
