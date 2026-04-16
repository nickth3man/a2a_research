from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import a2a_research.settings as settings_module
from a2a_research.settings import (
    AppSettings,
    ChromaSettings,
    EmbeddingSettings,
    LLMSettings,
    RAGSettings,
)


class TestValidateDotenvKeys:
    def test_unknown_keys_raise_value_error(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("UNKNOWN_KEY=value\nLLM_API_KEY=secret\n")

        with (
            patch("a2a_research.settings._ENV_FILE", env_file),
            pytest.raises(ValueError, match="Unknown keys in \\.env: UNKNOWN_KEY"),  # type: ignore[attr-defined]
        ):
            settings_module._validate_dotenv_keys()

    def test_mesop_passthrough_keys_are_allowed(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("MESOP_STATE_SESSION_BACKEND=memory\nLLM_API_KEY=secret\n")

        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings_module._validate_dotenv_keys()

    def test_expected_keys_are_allowed(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LOG_LEVEL=INFO\n"
            "MESOP_PORT=32123\n"
            "WORKFLOW_TIMEOUT=120\n"
            "LLM_PROVIDER=openrouter\n"
            "LLM_MODEL=m\n"
            "LLM_BASE_URL=https://example.com\n"
            "LLM_API_KEY=k\n"
            "EMBEDDING_MODEL=e\n"
            "EMBEDDING_PROVIDER=openai\n"
            "EMBEDDING_BASE_URL=https://e.com\n"
            "EMBEDDING_API_KEY=ek\n"
            "CHROMA_PERSIST_DIR=/tmp/chroma\n"
            "CHROMA_COLLECTION=c\n"
            "CHUNK_SIZE=512\n"
            "CHUNK_OVERLAP=64\n"
        )

        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings_module._validate_dotenv_keys()


class TestAppSettings:
    def test_model_validator_calls_dotenv_validation(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("BAD_KEY=value\n")

        with (
            patch("a2a_research.settings._ENV_FILE", env_file),
            pytest.raises(ValueError, match="Unknown keys"),  # type: ignore[attr-defined]
        ):
            AppSettings()

    def test_nested_settings_defaults(self) -> None:
        env_file = Path(__file__).resolve().parents[3] / ".env"
        if not env_file.exists():
            with (
                patch("a2a_research.settings._ENV_FILE", env_file),
                patch("a2a_research.settings.dotenv_values", return_value={}),
            ):
                settings = AppSettings()
        else:
            with patch("a2a_research.settings.dotenv_values", return_value={}):
                settings = AppSettings()

        assert isinstance(settings.llm, LLMSettings)
        assert isinstance(settings.embedding, EmbeddingSettings)
        assert isinstance(settings.chroma, ChromaSettings)
        assert isinstance(settings.rag, RAGSettings)

    def test_llm_settings_defaults(self) -> None:
        with (
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict("os.environ", {}, clear=True),
        ):
            llm = LLMSettings()
        assert llm.provider == "openrouter"
        assert llm.model == "openrouter/elephant-alpha"
        assert llm.base_url == "https://openrouter.ai/api/v1"
        assert isinstance(llm.api_key, str)

    def test_embedding_settings_defaults(self) -> None:
        with (
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict("os.environ", {}, clear=True),
        ):
            emb = EmbeddingSettings()
        assert emb.provider == "openrouter"
        assert emb.model == "perplexity/pplx-embed-v1-4b"
        assert emb.base_url == ""
        assert isinstance(emb.api_key, str)

    def test_chroma_settings_defaults(self) -> None:
        with patch("a2a_research.settings.dotenv_values", return_value={}):
            chroma = ChromaSettings()
        assert chroma.collection == "a2a_research"

    def test_rag_settings_defaults(self) -> None:
        with patch("a2a_research.settings.dotenv_values", return_value={}):
            rag = RAGSettings()
        assert rag.size == 512
        assert rag.overlap == 64
