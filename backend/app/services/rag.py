"""In-memory RAG store: chunk → embed → FAISS → retrieve.

FAISS holds vectors only. Parallel Python lists hold the original chunk text
and source labels (resume vs job_description). Nothing is written to disk.
"""

from __future__ import annotations

from dataclasses import dataclass

import faiss
import numpy as np

from app.core.config import settings
from app.services.chunking import chunk_text
from app.services.embeddings import LocalEmbedder


@dataclass(frozen=True)
class StoredChunk:
    chunk_id: int
    source: str
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    source: str
    text: str
    score: float


class InMemoryRagStore:
    def __init__(self, embedder: LocalEmbedder | None = None) -> None:
        self.embedder = embedder or LocalEmbedder()
        self._index: faiss.IndexFlatIP | None = None
        self.chunks: list[StoredChunk] = []

    def clear(self) -> None:
        self._index = None
        self.chunks = []

    @property
    def size(self) -> int:
        return len(self.chunks)

    def add_document(
        self,
        text: str,
        source: str,
        *,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> int:
        pieces = chunk_text(
            text,
            chunk_size=chunk_size or settings.rag_chunk_size,
            overlap=overlap if overlap is not None else settings.rag_chunk_overlap,
        )
        if not pieces:
            return 0

        vectors = self.embedder.embed(pieces)
        if vectors.ndim != 2 or vectors.shape[0] != len(pieces):
            raise RuntimeError("Embedding count did not match chunk count.")

        if self._index is None:
            self._index = faiss.IndexFlatIP(vectors.shape[1])
        elif self._index.d != vectors.shape[1]:
            raise RuntimeError("Embedding dimension changed; rebuild the index.")

        self._index.add(np.ascontiguousarray(vectors))
        for piece in pieces:
            self.chunks.append(
                StoredChunk(chunk_id=len(self.chunks), source=source, text=piece)
            )
        return len(pieces)

    def search(self, query: str, k: int | None = None) -> list[RetrievedChunk]:
        if self._index is None or self._index.ntotal == 0:
            return []

        query = query.strip()
        if not query:
            return []

        top_k = min(k or settings.rag_top_k, self._index.ntotal)
        query_vec = self.embedder.embed([query])
        scores, ids = self._index.search(np.ascontiguousarray(query_vec), top_k)

        results: list[RetrievedChunk] = []
        for score, idx in zip(scores[0].tolist(), ids[0].tolist(), strict=True):
            if idx < 0:
                continue
            stored = self.chunks[idx]
            results.append(
                RetrievedChunk(
                    chunk_id=stored.chunk_id,
                    source=stored.source,
                    text=stored.text,
                    score=float(score),
                )
            )
        return results
