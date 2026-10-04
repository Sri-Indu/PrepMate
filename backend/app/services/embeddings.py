"""Local text embeddings via sentence-transformers.

An embedding is a list of numbers that represents meaning. Similar sentences
land close together, which lets FAISS find relevant resume/JD passages.
The model runs on this machine; no API key is used.
"""

from __future__ import annotations

import numpy as np

from app.core.config import settings


class LocalEmbedder:
    """Lazy-loads one SentenceTransformer instance per process."""

    _model = None
    _model_name: str | None = None

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model

    def _get_model(self):
        if LocalEmbedder._model is None or LocalEmbedder._model_name != self.model_name:
            from huggingface_hub.errors import LocalEntryNotFoundError
            from sentence_transformers import SentenceTransformer

            try:
                LocalEmbedder._model = SentenceTransformer(
                    self.model_name,
                    local_files_only=True,
                )
            except (OSError, LocalEntryNotFoundError, ValueError):
                # First run: download weights into the local Hugging Face cache.
                LocalEmbedder._model = SentenceTransformer(self.model_name)
            LocalEmbedder._model_name = self.model_name
        return LocalEmbedder._model

    def embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        vectors = self._get_model().encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)
