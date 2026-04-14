"""RAG ingestion and retrieval using ChromaDB.

Ingestion: reads markdown files from data/corpus/, chunks them, and upserts
into a ChromaDB collection (created on first run).

Retrieval: queries the collection by semantic similarity and returns
ranked chunks with scores.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from a2a_research.models import DocumentChunk, RetrievedChunk
from a2a_research.settings import settings

_CORPUS_DIR = Path(__file__).resolve().parents[3] / "data" / "corpus"

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


def _chunk_text(
    text: str, size: int = settings.rag.size, overlap: int = settings.rag.overlap
) -> list[str]:
    overlap_chars = min(overlap, size // 4)
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


def ingest_corpus(force: bool = False) -> int:
    """Ingest corpus files into ChromaDB. Idempotent — skip if already populated."""
    collection = _get_collection()
    if not force and collection.count() > 0:
        return int(collection.count())

    from a2a_research.providers import get_embedder

    embedder = get_embedder()
    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    ids: list[str] = []

    corpus = _load_corpus_files()
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
        embeddings = embedder.embed_documents(docs)
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)

    return len(ids)


def retrieve(
    query: str,
    n_results: int = 10,
) -> list[RetrievedChunk]:
    """Query the ChromaDB collection by semantic similarity."""
    from a2a_research.providers import get_embedder

    collection = _get_collection()
    if collection.count() == 0:
        ingest_corpus()

    embedder = get_embedder()
    query_embedding = embedder.embed_query(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    retrieved: list[RetrievedChunk] = []
    raw_docs = results.get("documents") or []
    raw_metas = results.get("metadatas") or []
    raw_dists = results.get("distances") or []
    docs = raw_docs[0] if raw_docs else []
    metas = raw_metas[0] if raw_metas else []
    distances = raw_dists[0] if raw_dists else []

    if not docs:
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

    return retrieved


def get_source_title(source_key: str) -> str:
    """Look up a human-readable title for a source key."""
    corpus = _load_corpus_files()
    if source_key in corpus:
        match = re.match(r"^#\s+(.+)$", corpus[source_key], re.MULTILINE)
        if match:
            return match.group(1).strip()
    return source_key.replace("_", " ").title()
