"""Typed application settings loaded from the project ``.env`` and environment.

Prefixes (Pydantic ``BaseSettings``):

- ``LLM_*`` — chat model provider, model id, base URL, API key.
- ``EMBEDDING_*`` — embedding provider, model, URLs, key.
- ``CHROMA_*`` — vector DB path and collection name.
- ``CHUNK_*`` — RAG chunk size and overlap (see :class:`RAGSettings`).

Unprefixed fields on :class:`AppSettings`: ``LOG_LEVEL``, ``MESOP_PORT``.

Mesop reads additional ``MESOP_*`` variables (for example ``MESOP_STATE_SESSION_BACKEND``)
via its own library config; those are documented in ``.env.example``, not as fields here.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

__all__ = [
    "settings",
    "AppSettings",
    "LLMSettings",
    "EmbeddingSettings",
    "ChromaSettings",
    "RAGSettings",
]


class LLMSettings(BaseSettings):
    """LLM provider configuration — vendor-agnostic."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        extra="forbid",
    )

    provider: str = Field(
        default="openrouter",
        description="LLM provider: openrouter | openai | anthropic | google | ollama",
    )
    model: str = Field(
        default="openrouter/elephant-alpha",
        description="Model identifier (provider-specific).",
    )
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenAI-compatible base URL override (blank = provider default).",
    )
    api_key: str = Field(
        default="",
        description="API key for the chosen provider.",
    )


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="EMBEDDING_",
        extra="forbid",
    )

    model: str = Field(
        default="perplexity/pplx-embed-v1-4b",
        description="Embedding model name.",
    )
    provider: str = Field(
        default="openrouter",
        description="Embedding provider: openrouter | openai | ollama",
    )
    base_url: str = Field(
        default="",
        description="Separate base URL for embeddings (blank = same as LLM).",
    )
    api_key: str = Field(
        default="",
        description="Embedding API key (blank = same as LLM_API_KEY).",
    )


class ChromaSettings(BaseSettings):
    """ChromaDB vector-store configuration."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="CHROMA_",
        extra="forbid",
    )

    persist_dir: Path = Field(
        default=_PROJECT_ROOT / "data" / "chroma",
        description="Directory for persistent ChromaDB storage.",
    )
    collection: str = Field(
        default="a2a_research",
        description="Default ChromaDB collection name.",
    )


class RAGSettings(BaseSettings):
    """RAG chunking parameters."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="CHUNK_",
        extra="forbid",
    )

    size: int = Field(default=512, description="Chunk size in tokens.")
    overlap: int = Field(default=64, description="Overlap between chunks.")


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="forbid",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, or ERROR (env: LOG_LEVEL).",
    )
    mesop_port: int = Field(
        default=32123,
        description="Default port for the Mesop UI in app tooling (env: MESOP_PORT).",
    )
    workflow_timeout: float = Field(
        default=120.0,
        description="Maximum workflow runtime in seconds before returning a partial timed-out session.",
    )

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)


settings = AppSettings()
