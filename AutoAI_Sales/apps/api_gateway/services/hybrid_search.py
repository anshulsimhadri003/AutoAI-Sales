from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log
import re
from typing import Any, Callable

import numpy as np

try:  # pragma: no cover - optional dependency behavior
    import faiss
except Exception:  # pragma: no cover
    faiss = None

from shared.config.settings import get_settings
from shared.integrations.embedding_client import EmbeddingClient

TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class HybridDocument:
    doc_id: str
    text: str
    metadata: dict[str, Any]


class HybridSearchIndex:
    def __init__(
        self,
        name: str,
        documents: list[HybridDocument],
        *,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self.name = name
        self.documents = documents
        self.embedding_client = embedding_client or EmbeddingClient()
        self.settings = get_settings()
        self.semantic_weight = self.settings.semantic_semantic_weight
        self.lexical_weight = self.settings.semantic_lexical_weight

        self._tokenized_docs = [self._tokenize(doc.text) for doc in self.documents]
        self._doc_lengths = [len(tokens) for tokens in self._tokenized_docs]
        self._avg_doc_length = max(sum(self._doc_lengths) / max(len(self._doc_lengths), 1), 1.0)
        self._idf = self._compute_idf(self._tokenized_docs)
        self._embeddings = self._build_embedding_matrix([doc.text for doc in self.documents])
        self._faiss_index = self._build_faiss_index(self._embeddings)

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        score_boost: Callable[[HybridDocument], float] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.documents:
            return []
        query = (query or "").strip()
        query_embedding = self._build_embedding_matrix([query])
        semantic_scores = self._semantic_scores(query_embedding)
        lexical_scores = self._lexical_scores(query)
        semantic_scores = self._normalize(semantic_scores)
        lexical_scores = self._normalize(lexical_scores)

        ranked: list[dict[str, Any]] = []
        for idx, doc in enumerate(self.documents):
            if filters and not self._matches_filters(doc.metadata, filters):
                continue
            boost = score_boost(doc) if score_boost else 0.0
            score = (self.semantic_weight * semantic_scores[idx]) + (self.lexical_weight * lexical_scores[idx]) + boost
            ranked.append(
                {
                    "doc_id": doc.doc_id,
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "semantic_score": round(float(semantic_scores[idx]), 4),
                    "lexical_score": round(float(lexical_scores[idx]), 4),
                    "score": round(float(score), 4),
                }
            )
        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]

    def pair_score(self, query_text: str, document_text: str) -> float:
        if not query_text and not document_text:
            return 0.0
        temp_index = HybridSearchIndex(
            name=f"{self.name}-pair",
            documents=[HybridDocument(doc_id="pair", text=document_text, metadata={})],
            embedding_client=self.embedding_client,
        )
        results = temp_index.search(query_text, top_k=1)
        return results[0]["score"] if results else 0.0

    def _tokenize(self, text: str) -> list[str]:
        return TOKEN_RE.findall((text or "").lower())

    def _compute_idf(self, tokenized_docs: list[list[str]]) -> dict[str, float]:
        document_count = len(tokenized_docs)
        frequencies = Counter()
        for tokens in tokenized_docs:
            frequencies.update(set(tokens))
        return {token: log(1 + ((document_count - freq + 0.5) / (freq + 0.5))) for token, freq in frequencies.items()}

    def _lexical_scores(self, query: str) -> np.ndarray:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return np.zeros(len(self.documents), dtype=np.float32)
        scores = np.zeros(len(self.documents), dtype=np.float32)
        k1 = 1.5
        b = 0.75
        for doc_idx, tokens in enumerate(self._tokenized_docs):
            term_freq = Counter(tokens)
            doc_length = max(self._doc_lengths[doc_idx], 1)
            score = 0.0
            for token in query_tokens:
                if token not in term_freq:
                    continue
                freq = term_freq[token]
                idf = self._idf.get(token, 0.0)
                numerator = freq * (k1 + 1)
                denominator = freq + k1 * (1 - b + b * (doc_length / self._avg_doc_length))
                score += idf * (numerator / max(denominator, 1e-9))
            scores[doc_idx] = score
        return scores

    def _build_embedding_matrix(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.settings.semantic_vector_dimensions), dtype=np.float32)
        matrix = np.asarray(self.embedding_client.embed(texts), dtype=np.float32)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def _build_faiss_index(self, embeddings: np.ndarray):
        if embeddings.size == 0 or faiss is None or not self.settings.semantic_faiss_enabled:
            return None
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        return index

    def _semantic_scores(self, query_embedding: np.ndarray) -> np.ndarray:
        if self._embeddings.size == 0:
            return np.zeros(0, dtype=np.float32)
        if self._faiss_index is not None:
            scores, _ = self._faiss_index.search(query_embedding.astype(np.float32), len(self.documents))
            return scores[0]
        return np.matmul(self._embeddings, query_embedding[0])

    def _matches_filters(self, metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, expected in filters.items():
            value = metadata.get(key)
            if expected is None:
                continue
            if isinstance(expected, set):
                if value not in expected:
                    return False
                continue
            if isinstance(expected, (list, tuple)):
                if value not in expected:
                    return False
                continue
            if value != expected:
                return False
        return True

    def _normalize(self, values: np.ndarray) -> np.ndarray:
        if values.size == 0:
            return values
        min_value = float(np.min(values))
        max_value = float(np.max(values))
        if max_value - min_value < 1e-9:
            if max_value <= 0:
                return np.zeros_like(values)
            return np.ones_like(values)
        return (values - min_value) / (max_value - min_value)
