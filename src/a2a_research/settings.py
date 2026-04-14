"""Typed application settings loaded from environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class LLMSettings(BaseSettings):
    """LLM provider configuration — vendor-agnostic."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    provider: str = Field(
        default="openai",
        description="LLM provider: openai | anthropic | google | ollama",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="Model identifier (provider-specific).",
    )
    base_url: str = Field(
        default="",
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
        extra="ignore",
    )

    model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name.",
    )
    provider: str = Field(
        default="openai",
        description="Embedding provider: openai | ollama | huggingface.",
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
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_prefix="CHUNK_",
        extra="ignore",
    )

    size: int = Field(default=512, description="Chunk size in tokens.")
    overlap: int = Field(default=64, description="Overlap between chunks.")


class AppSettings(BaseSettings):
    """Top-level application settings."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO", description="DEBUG | INFO | WARNING | ERROR")
    mesop_port: int = Field(default=32123, description="Mesop UI server port.")

    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    chroma: ChromaSettings = Field(default_factory=ChromaSettings)
    rag: RAGSettings = Field(default_factory=RAGSettings)


settings = AppSettings()
