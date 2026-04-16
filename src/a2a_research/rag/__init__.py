"""RAG ingestion and retrieval using ChromaDB.

Ingestion: reads markdown files from ``data/corpus/`` (under the repo root), chunks
them using :class:`~a2a_research.settings.RAGSettings`, and upserts into a collection
(configured via ``CHROMA_*`` settings).

Retrieval: embeds the query with the configured embedding provider, queries Chroma,
and returns ranked :class:`~a2a_research.models.RetrievedChunk` values with scores.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any

from a2a_research.app_logging import get_logger
from a2a_research.models import DocumentChunk, RetrievedChunk
from a2a_research.settings import settings

__all__ = [
    "ensure_corpus_ingested",
    "ingest_corpus",
    "retrieve_chunks",
    "get_source_title",
    "reset_rag_singletons",
]

_CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "corpus"
logger = get_logger(__name__)

# ChromaDB client (lazily initialised — requires chromadb package at runtime)
_chroma_client: Any = None
_collection: Any = None


def _get_chroma_client() -> Any:
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        _chroma_client = chromadb.PersistentClient(path=str(settings.chroma.persist_dir))
    return _chroma_client


def _get_collection() -> Any:
    global _collection
    if _collection is None:
        client = _get_chroma_client()
        _collection = client.get_or_create_collection(
            name=settings.chroma.collection,
            metadata={"description": "A2A Research corpus"},
        )
    return _collection


def _is_dimension_mismatch_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "expecting embedding with dimension" in message and "got" in message


def _reset_collection(reason: str) -> Any:
    global _collection
    client = _get_chroma_client()
    logger.warning(
        "RAG resetting collection name=%s reason=%s", settings.chroma.collection, reason
    )
    try:
        client.delete_collection(name=settings.chroma.collection)
    except Exception:
        logger.exception("RAG collection reset failed name=%s", settings.chroma.collection)
        raise

    _collection = client.get_or_create_collection(
        name=settings.chroma.collection,
        metadata={"description": "A2A Research corpus"},
    )
    return _collection


def _query_collection(
    collection: Any,
    *,
    query_embedding: list[float],
    n_results: int,
) -> Any:
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )


def _chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    _size = size if size is not None else settings.rag.size
    _overlap = overlap if overlap is not None else settings.rag.overlap
    overlap_chars = min(_overlap, _size // 4)
    if len(text) <= _size:
        return [text] if text.strip() else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + _size
        chunk = text[start:end]
        sentences = re.split(r"(?<=[.!?])\s+", chunk)
        if len(sentences) > 1 and sentences[-1]:
            last_complete = sentences[-1]
            chunks.append(chunk[: len(chunk) - len(last_complete)].strip())
            start = end - len(last_complete)
        else:
            chunks.append(chunk.strip())
            start = end - overlap_chars
    return [c for c in chunks if c.strip()]
    if len(text) <= size:
        return [text] if text.strip() else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        sentences = re.split(r"(?<=[.!?])\s+", chunk)
        if len(sentences) > 1 and sentences[-1]:
            last_complete = sentences[-1]
            chunks.append(chunk[: len(chunk) - len(last_complete)].strip())
            start = end - len(last_complete)
        else:
            chunks.append(chunk.strip())
            start = end - overlap_chars
    return [c for c in chunks if c.strip()]


def _load_corpus_files() -> dict[str, str]:
    """Load all markdown files from the corpus directory."""
    contents: dict[str, str] = {}
    if not _CORPUS_DIR.exists():
        return contents
    for md_file in _CORPUS_DIR.glob("*.md"):
        contents[md_file.stem] = md_file.read_text(encoding="utf-8")
    return contents


def ensure_corpus_ingested(*, force: bool = False) -> int:
    """Prepare the vector store outside request-time retrieval when desired."""
    return ingest_corpus(force=force)


def ingest_corpus(force: bool = False) -> int:
    """Ingest corpus files into ChromaDB. Idempotent — skip if already populated."""
    collection = _get_collection()
    if not force and collection.count() > 0:
        logger.info("RAG ingest skipped existing_chunks=%s force=%s", collection.count(), force)
        return int(collection.count())

    from a2a_research.providers import get_embedder

    embedder = get_embedder()
    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    ids: list[str] = []

    corpus = _load_corpus_files()
    logger.info("RAG ingest start corpus_files=%s force=%s", len(corpus), force)
    chunk_id = 0
    for source_name, content in corpus.items():
        title_match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else source_name
        chunks = _chunk_text(content)
        for idx, chunk_text in enumerate(chunks):
            if not chunk_text.strip():
                continue
            docs.append(chunk_text)
            metas.append({"source": source_name, "title": title, "chunk_index": idx})
            ids.append(f"chunk_{chunk_id}")
            chunk_id += 1

    if docs:
        started_at = perf_counter()
        logger.info("RAG ingest embedding chunks=%s", len(docs))
        embeddings = embedder.embed_documents(docs)
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.info("RAG ingest upserted chunks=%s elapsed_ms=%.1f", len(ids), elapsed_ms)
    else:
        logger.info("RAG ingest found no chunks to index")

    return len(ids)


def retrieve_chunks(
    query: str,
    n_results: int = 10,
) -> list[RetrievedChunk]:
    """Query the ChromaDB collection by semantic similarity."""
    from a2a_research.providers import get_embedder

    collection = _get_collection()
    if collection.count() == 0:
        logger.info("RAG retrieve query=%r collection_empty=true", query)
        ensure_corpus_ingested()

    embedder = get_embedder()
    started_at = perf_counter()
    logger.info(
        "RAG retrieve start query=%r n_results=%s collection_count=%s",
        query,
        n_results,
        collection.count(),
    )
    query_embedding = embedder.embed_query(query)
    try:
        results = _query_collection(
            collection,
            query_embedding=query_embedding,
            n_results=n_results,
        )
    except Exception as exc:
        if not _is_dimension_mismatch_error(exc):
            raise

        logger.warning(
            "RAG retrieve detected embedding dimension mismatch query=%r error=%s",
            query,
            exc,
        )
        collection = _reset_collection("embedding dimension mismatch")
        ingest_corpus(force=True)
        results = _query_collection(
            collection,
            query_embedding=query_embedding,
            n_results=n_results,
        )

    retrieved: list[RetrievedChunk] = []
    raw_docs = results.get("documents") or []
    raw_metas = results.get("metadatas") or []
    raw_dists = results.get("distances") or []
    docs = raw_docs[0] if raw_docs else []
    metas = raw_metas[0] if raw_metas else []
    distances = raw_dists[0] if raw_dists else []

    if not docs:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.info("RAG retrieve completed query=%r results=0 elapsed_ms=%.1f", query, elapsed_ms)
        return retrieved

    for doc_item, meta_item, dist in zip(docs, metas, distances, strict=False):
        if not doc_item:
            continue
        score = 1.0 - min(dist, 1.0) if dist is not None else 0.0
        chunk = DocumentChunk(
            id=f"chunk_{meta_item.get('source', 'unknown')}_{meta_item.get('chunk_index', 0)}",
            content=doc_item,
            source=meta_item.get("source", "unknown"),
            chunk_index=meta_item.get("chunk_index", 0),
            metadata={"title": meta_item.get("title", "")},
        )
        retrieved.append(RetrievedChunk(chunk=chunk, score=score))

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "RAG retrieve completed query=%r results=%s elapsed_ms=%.1f",
        query,
        len(retrieved),
        elapsed_ms,
    )
    return retrieved


@lru_cache(maxsize=256)
def get_source_title(source_key: str) -> str:
    """Look up a human-readable title for a source key."""
    corpus = _load_corpus_files()
    if source_key in corpus:
        match = re.match(r"^#\s+(.+)$", corpus[source_key], re.MULTILINE)
        if match:
            return match.group(1).strip()
    return source_key.replace("_", " ").title()


def reset_rag_singletons() -> None:
    global _chroma_client, _collection
    _chroma_client = None
    _collection = None
    get_source_title.cache_clear()
