from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)


TOKEN_RE = re.compile(r"[a-z0-9]+")


class EmbeddingClient:
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        if OpenAI and self.settings.enable_openai and self.settings.openai_api_key:
            self.client = OpenAI(api_key=self.settings.openai_api_key, timeout=self.settings.openai_timeout_seconds)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self.client:
            try:
                response = self.client.embeddings.create(
                    model=self.settings.openai_embedding_model,
                    input=texts,
                )
                return [item.embedding for item in response.data]
            except Exception:
                logger.exception("OpenAI embedding call failed, falling back to hash embeddings")
        return [self._hash_embed(text) for text in texts]

    def _hash_embed(self, text: str) -> list[float]:
        dims = self.settings.semantic_vector_dimensions
        vec = [0.0] * dims
        normalized_text = (text or "").lower().strip()
        tokens = TOKEN_RE.findall(normalized_text)
        counts = Counter(tokens)
        if not counts and not normalized_text:
            return vec
        total = max(sum(counts.values()), 1)
        for token, count in counts.items():
            idx = self._stable_index(f"tok::{token}", dims)
            vec[idx] += 0.75 * (count / total)
        compact = normalized_text.replace(" ", "")
        ngrams = [compact[i : i + 3] for i in range(max(len(compact) - 2, 0))]
        if compact and not ngrams:
            ngrams = [compact]
        if ngrams:
            ngram_counts = Counter(ngrams)
            ngram_total = sum(ngram_counts.values())
            for ngram, count in ngram_counts.items():
                idx = self._stable_index(f"ng::{ngram}", dims)
                vec[idx] += 0.35 * (count / ngram_total)
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            return vec
        return [v / norm for v in vec]

    def _stable_index(self, text: str, dims: int) -> int:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big") % dims


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
