"""LLM protocol and test implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class ChatResponse:
    """Simple response wrapper compatible with the existing agent interface."""

    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str = ""
    model: str = ""


@runtime_checkable
class ChatModelProtocol(Protocol):
    """Protocol for async chat model implementations."""

    async def ainvoke(self, messages: list[dict[str, str]]) -> ChatResponse:
        """Invoke the model with a list of messages and return a response."""


class TestChatModel:
    """Test chat model that returns a configurable fixed response."""

    def __init__(self, response_text: str = "test response") -> None:
        self._response_text = response_text

    async def ainvoke(self, messages: list[dict[str, str]]) -> ChatResponse:
        return ChatResponse(content=self._response_text)
