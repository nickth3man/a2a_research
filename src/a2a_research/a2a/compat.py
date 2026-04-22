"""Compatibility helpers for the installed A2A SDK version."""

from __future__ import annotations

from typing import Any

from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette

__all__ = ["build_http_app", "make_agent_card", "make_skill"]


def make_skill(
    *,
    skill_id: str,
    name: str,
    description: str,
    tags: list[str] | None = None,
    examples: list[str] | None = None,
    input_modes: list[str] | None = None,
    output_modes: list[str] | None = None,
) -> AgentSkill:
    return AgentSkill(
        id=skill_id,
        name=name,
        description=description,
        tags=list(tags or []),
        examples=list(examples or []),
        input_modes=list(input_modes or []),
        output_modes=list(output_modes or []),
    )


def make_agent_card(
    *,
    name: str,
    description: str,
    url: str,
    version: str = "1.0.0",
    streaming: bool = False,
    push_notifications: bool = False,
    skills: list[AgentSkill] | None = None,
    default_input_modes: list[str] | None = None,
    default_output_modes: list[str] | None = None,
    protocol_binding: str = "JSONRPC",
    protocol_version: str = "1.0.0",
) -> AgentCard:
    return AgentCard(
        name=name,
        description=description,
        supported_interfaces=[
            AgentInterface(
                url=url,
                protocol_binding=protocol_binding,
                protocol_version=protocol_version,
            )
        ],
        version=version,
        capabilities=AgentCapabilities(
            streaming=streaming,
            push_notifications=push_notifications,
        ),
        default_input_modes=list(default_input_modes or []),
        default_output_modes=list(default_output_modes or []),
        skills=list(skills or []),
    )


def build_http_app(*, agent_card: AgentCard, http_handler: Any) -> Starlette:
    routes = [
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(
            http_handler, rpc_url="/", enable_v0_3_compat=True
        ),
    ]
    return Starlette(routes=routes)
