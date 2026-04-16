"""Tests for RAG ingestion/retrieval and A2A contracts - no API keys needed."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from a2a_research.a2a import A2AClient, A2AServer
from a2a_research.models import (
    A2AMessage,
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)
from a2a_research.rag import _chunk_text, _load_corpus_files, get_source_title


class TestRAGHelpers:
    def test_chunk_text_small(self):
        text = "This is a short text."
        chunks = _chunk_text(text, size=512, overlap=64)
        assert len(chunks) == 1
        assert chunks[0] == "This is a short text."

    def test_chunk_text_exactly_size(self):
        text = "a" * 512
        chunks = _chunk_text(text, size=512, overlap=64)
        assert len(chunks) == 1
        assert chunks[0] == "a" * 512

    def test_chunk_text_empty(self):
        assert _chunk_text("", size=512, overlap=64) == []
        assert _chunk_text("   ", size=512, overlap=64) == []

    def test_chunk_text_long(self):
        text = "This is sentence one. " * 100
        chunks = _chunk_text(text, size=200, overlap=50)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk.strip()) > 0

    def test_load_corpus_files(self):
        corpus = _load_corpus_files()
        assert isinstance(corpus, dict)
        assert len(corpus) >= 4

    def test_get_source_title_existing(self):
        title = get_source_title("a2a_protocols")
        assert isinstance(title, str)
        assert len(title) > 0

    def test_get_source_title_unknown(self):
        title = get_source_title("nonexistent_source_xyz")
        assert isinstance(title, str)


class TestA2AClient:
    def test_a2a_message_creation(self):
        msg = A2AMessage(
            sender=AgentRole.RESEARCHER,
            recipient=AgentRole.ANALYST,
            task_id="task_1",
            payload={"query": "What is RAG?"},
        )
        assert msg.sender == AgentRole.RESEARCHER
        assert msg.recipient == AgentRole.ANALYST
        assert msg.task_id == "task_1"
        assert msg.payload["query"] == "What is RAG?"

    def test_a2a_message_auto_id(self):
        msg = A2AMessage(sender=AgentRole.ANALYST, recipient=AgentRole.VERIFIER)
        assert msg.task_id is not None
        assert len(msg.task_id) > 0

    def test_a2a_client_role(self):
        client = A2AClient(AgentRole.RESEARCHER)
        assert client.role == AgentRole.RESEARCHER

    def test_a2a_server_role(self):
        server = A2AServer(AgentRole.VERIFIER)
        assert server.role == AgentRole.VERIFIER

    def test_a2a_client_dispatches_to_analyst(self):
        mock_response = MagicMock()
        mock_response.content = '{"atomic_claims": [{"id": "c1", "text": "Test claim"}]}'

        with patch("a2a_research.agents._call_llm", return_value=mock_response.content):
            client = A2AClient(AgentRole.RESEARCHER)
            session = ResearchSession(query="Test query")
            session.agent_results[AgentRole.RESEARCHER] = AgentResult(
                role=AgentRole.RESEARCHER,
                status=AgentStatus.COMPLETED,
                raw_content="RAG is a technique.",
                citations=["doc1"],
            )
            msg = A2AMessage(
                sender=AgentRole.RESEARCHER,
                recipient=AgentRole.ANALYST,
                payload={},
            )
            result = client.send(msg, session)
            assert result.role == AgentRole.ANALYST


# Default embedding model (perplexity/pplx-embed-v1-4b) uses 2560-dimensional vectors.
_EMBED_DIM = 2560


class TestRAGWithMocks:
    def test_ingest_with_mocked_embeddings(self):
        mock_embedder = MagicMock()
        # Corpus has 4 files producing ~15 chunks; match that count
        mock_embedder.embed_documents.return_value = [[0.1] * _EMBED_DIM] * 15

        with patch("a2a_research.providers.get_embedder", return_value=mock_embedder):
            from a2a_research.rag import _get_collection, ingest_corpus

            count = ingest_corpus(force=True)
            assert count == 15
            coll = _get_collection()
            assert coll.count() == 15

    def test_retrieve_returns_chunks_with_mock(self):
        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * _EMBED_DIM

        mock_coll = MagicMock()
        mock_coll.count.return_value = 5
        # ChromaDB query returns: documents=[[d1, d2, d3]], metadatas=[[m1, m2, m3]]
        mock_coll.query.return_value = {
            "documents": [["RAG is effective.", "RAG uses embeddings.", "RAG is from Facebook."]],
            "metadatas": [
                [
                    {"source": "rag_accuracy", "chunk_index": 0, "title": "RAG Study"},
                    {"source": "a2a_protocols", "chunk_index": 1, "title": "A2A Protocols"},
                    {
                        "source": "claim_verification",
                        "chunk_index": 0,
                        "title": "Claim Verification",
                    },
                ]
            ],
            "distances": [[0.1, 0.5, 0.9]],
        }

        with (
            patch("a2a_research.rag._chroma_client", mock_coll),
            patch("a2a_research.rag._collection", mock_coll),
            patch("a2a_research.providers.get_embedder", return_value=mock_embedder),
        ):
            from a2a_research.rag import RetrievedChunk, retrieve_chunks

            chunks = retrieve_chunks("Is RAG effective?", n_results=3)
            assert len(chunks) == 3
            assert all(isinstance(rc, RetrievedChunk) for rc in chunks)
            assert all(0.0 <= rc.score <= 1.0 for rc in chunks)

    def test_retrieve_empty_results(self):
        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * _EMBED_DIM

        mock_coll = MagicMock()
        mock_coll.count.return_value = 0
        mock_coll.query.return_value = {
            "documents": [],
            "metadatas": [],
            "distances": [],
        }

        with (
            patch("a2a_research.rag._chroma_client", mock_coll),
            patch("a2a_research.rag._collection", mock_coll),
            patch("a2a_research.providers.get_embedder", return_value=mock_embedder),
        ):
            from a2a_research.rag import retrieve_chunks

            chunks = retrieve_chunks("Does not exist xyz abc", n_results=5)
            assert len(chunks) == 0

    def test_retrieve_recovers_from_dimension_mismatch(self):
        class DimensionMismatchError(Exception):
            pass

        mock_embedder = MagicMock()
        mock_embedder.embed_query.return_value = [0.1] * 2560

        stale_collection = MagicMock()
        stale_collection.count.return_value = 5
        stale_collection.query.side_effect = DimensionMismatchError(
            "Collection expecting embedding with dimension of 2560, got 1536"
        )

        recovered_collection = MagicMock()
        recovered_collection.query.return_value = {
            "documents": [["Recovered chunk"]],
            "metadatas": [[{"source": "rag_accuracy", "chunk_index": 0, "title": "Recovered"}]],
            "distances": [[0.1]],
        }

        with (
            patch("a2a_research.rag._collection", stale_collection),
            patch("a2a_research.providers.get_embedder", return_value=mock_embedder),
            patch(
                "a2a_research.rag._reset_collection", return_value=recovered_collection
            ) as reset_collection,
            patch("a2a_research.rag.ingest_corpus") as ingest_corpus,
        ):
            from a2a_research.rag import retrieve_chunks

            chunks = retrieve_chunks("Is RAG effective?", n_results=1)

        assert len(chunks) == 1
        reset_collection.assert_called_once()
        ingest_corpus.assert_called_once_with(force=True)
