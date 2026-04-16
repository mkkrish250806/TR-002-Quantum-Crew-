from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from services.embeddings import EmbeddingService


class VectorStore:
    def __init__(self, kb_path: str, embedding_service: EmbeddingService) -> None:
        self.kb_path = Path(kb_path)
        self.embedding_service = embedding_service
        self.documents: list[dict[str, Any]] = []
        self.index: faiss.IndexFlatL2 | None = None
        self._load_and_index()

    def _load_and_index(self) -> None:
        with self.kb_path.open("r", encoding="utf-8") as f:
            self.documents = json.load(f)

        corpus = [doc["text"] for doc in self.documents]
        embeddings = self.embedding_service.embed_texts(corpus)
        faiss.normalize_L2(embeddings)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)

    @staticmethod
    def _l2_to_similarity(distance: float) -> float:
        # For normalized sentence embeddings, L2 distance is usually within [0, ~4].
        # Convert to an intuitive similarity where higher is better.
        similarity = 1.0 - (distance / 4.0)
        return float(max(0.0, min(1.0, similarity)))

    def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if self.index is None:
            return []

        query_embedding = self.embedding_service.embed_query(query)
        faiss.normalize_L2(query_embedding)
        distances, indices = self.index.search(query_embedding, top_k)

        results: list[dict[str, Any]] = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            doc = self.documents[int(idx)]
            results.append(
                {
                    "id": doc["id"],
                    "title": doc.get("title", doc["id"]),
                    "text": doc["text"],
                    "type": doc.get("type", "unknown"),
                    "similarity": self._l2_to_similarity(float(distance)),
                }
            )
        return results
