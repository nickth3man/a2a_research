"""Typed application settings loaded from the project ``.env`` and environment.

Prefixes (Pydantic ``BaseSettings``):

- ``LLM_*`` — chat model provider, model id, base URL, API key.
- ``EMBEDDING_*`` — embedding provider, model, URLs, key.
- ``CHROMA_*`` — vector DB path and collection name.
- ``CHUNK_*`` — RAG chunk size and overlap (see :class:`RAGSettings`).

Unprefixed fields on :class:`AppSettings`: ``LOG_LEVEL``, ``MESOP_PORT``,
``WORKFLOW_TIMEOUT``.

Mesop reads additional ``MESOP_*`` variables (for example
``MESOP_STATE_SESSION_BACKEND``) via its own library config.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"

__all__ = [
    "AppSettings",
    "ChromaSettings",
    "EmbeddingSettings",
    "LLMSettings",
    "RAGSettings",
    "settings",
]


class LLMSettings(BaseSettings):
    """LLM provider configuration — vendor-agnostic."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        env_prefix="LLM_",
        extra="ignore",
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
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        env_prefix="EMBEDDING_",
        extra="ignore",
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
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        env_prefix="CHROMA_",
        extra="ignore",
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
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        env_prefix="CHUNK_",
        extra="ignore",
    )

    size: int = Field(default=512, description="Chunk size in tokens.")
    overlap: int = Field(default=64, description="Overlap between chunks.")


def _expected_prefixed_keys(settings_cls: type[BaseSettings]) -> set[str]:
    prefix = str(settings_cls.model_config.get("env_prefix") or "").upper()
    return {f"{prefix}{name}".upper() for name in settings_cls.model_fields}


_EXPECTED_DOTENV_KEYS = {
    "LOG_LEVEL",
    "MESOP_PORT",
    "WORKFLOW_TIMEOUT",
    *_expected_prefixed_keys(LLMSettings),
    *_expected_prefixed_keys(EmbeddingSettings),
    *_expected_prefixed_keys(ChromaSettings),
    *_expected_prefixed_keys(RAGSettings),
}

_PASSTHROUGH_PREFIXES = ("MESOP_",)


def _validate_dotenv_keys() -> None:
    raw_values = dotenv_values(_ENV_FILE)
    unknown_keys: list[str] = []

    for key in raw_values:
        if key is None:
            continue

        normalized = key.upper()

        if normalized in _EXPECTED_DOTENV_KEYS:
            continue

        if any(normalized.startswith(prefix) for prefix in _PASSTHROUGH_PREFIXES):
            continue

        unknown_keys.append(key)

    if unknown_keys:
        rendered = ", ".join(sorted(unknown_keys))
        raise ValueError(
            "Unknown keys in .env: "
            f"{rendered}. "
            "Allowed project keys are LOG_LEVEL, MESOP_PORT, WORKFLOW_TIMEOUT, "
            "and keys under the LLM_, EMBEDDING_, CHROMA_, and CHUNK_ prefixes. "
            "MESOP_* keys are allowed as passthrough."
        )


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
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

    @model_validator(mode="after")
    def validate_dotenv_contract(self) -> AppSettings:
        _validate_dotenv_keys()
        return self


settings = AppSettings()
