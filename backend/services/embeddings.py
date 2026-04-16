from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return np.array(embeddings, dtype="float32")

    def embed_query(self, query: str) -> np.ndarray:
        embedding = self.model.encode([query], show_progress_bar=False)
        return np.array(embedding, dtype="float32")
