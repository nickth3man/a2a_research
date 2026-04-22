"""LLM configuration settings (OpenRouter)."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["LLMSettings"]


class LLMSettings(BaseSettings):
    """OpenRouter configuration used by every LLM integration."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        extra="ignore",
    )

    model: str = Field(
        default="openrouter/elephant-alpha",
        description="OpenRouter model identifier.",
    )
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter base URL.",
    )
    api_key: str = Field(
        default="",
        description="OpenRouter API key (env: LLM_API_KEY).",
    )
