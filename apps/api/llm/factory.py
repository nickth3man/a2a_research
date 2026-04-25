"""Factory for creating chat model instances."""

from __future__ import annotations

import os

from llm.protocol import ChatModelProtocol, TestChatModel
from llm.providers import OpenRouterChatModel

_MODEL_REGISTRY: dict[str, type[ChatModelProtocol]] = {
    "openrouter": OpenRouterChatModel,
    "test": TestChatModel,
}


def create_chat_model(model_name: str | None = None) -> ChatModelProtocol:
    """Create a chat model instance.

    Returns TestChatModel when A2A_TEST_MODE environment variable is set,
    otherwise returns OpenRouterChatModel.
    """
    if os.environ.get("A2A_TEST_MODE"):
        return _MODEL_REGISTRY["test"]()
    return _MODEL_REGISTRY["openrouter"](model=model_name)  # type: ignore[call-arg]
