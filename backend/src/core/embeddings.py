"""Embedding service with HuggingFace MCP and local fallback."""

import logging
from typing import Protocol

import numpy as np
from sentence_transformers import SentenceTransformer

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @property
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        ...


class LocalEmbeddingProvider:
    """Local embedding provider using sentence-transformers."""

    def __init__(self, model_name: str = None):
        """Initialize the local embedding model.

        Args:
            model_name: Name of the sentence-transformers model.
        """
        self._model_name = model_name or settings.embedding_model
        self._model: SentenceTransformer | None = None
        self._dimensions = settings.embedding_dimensions

    def _load_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            # Update dimensions from actual model
            self._dimensions = self._model.get_sentence_embedding_dimension()
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        model = self._load_model()

        # Generate embeddings
        embeddings = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalize for cosine similarity
            show_progress_bar=False,
        )

        return embeddings.tolist()

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        embeddings = await self.embed([text])
        return embeddings[0] if embeddings else []

    @property
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        return self._dimensions


class HuggingFaceMCPProvider:
    """HuggingFace MCP embedding provider (placeholder for MCP integration)."""

    def __init__(self):
        """Initialize HF MCP provider."""
        self._dimensions = settings.embedding_dimensions
        self._fallback = LocalEmbeddingProvider()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using HuggingFace MCP.

        Falls back to local if MCP unavailable.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        # TODO: Implement actual HuggingFace MCP integration
        # For now, use local fallback
        logger.debug("Using local fallback for embeddings (HF MCP not implemented)")
        return await self._fallback.embed(texts)

    @property
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        return self._dimensions


class EmbeddingService:
    """Main embedding service with provider selection and fallback."""

    def __init__(self, prefer_mcp: bool = True):
        """Initialize embedding service.

        Args:
            prefer_mcp: If True, prefer HuggingFace MCP over local.
        """
        self._local = LocalEmbeddingProvider()
        self._mcp = HuggingFaceMCPProvider() if prefer_mcp else None
        self._prefer_mcp = prefer_mcp

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings with automatic fallback.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        if self._prefer_mcp and self._mcp:
            try:
                return await self._mcp.embed(texts)
            except Exception as e:
                logger.warning(f"MCP embedding failed, falling back to local: {e}")

        return await self._local.embed(texts)

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        embeddings = await self.embed([text])
        return embeddings[0] if embeddings else []

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """Generate embeddings in batches.

        Args:
            texts: List of texts to embed.
            batch_size: Number of texts per batch.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await self.embed(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    @property
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        return self._local.dimensions

    @staticmethod
    def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Cosine similarity score (-1 to 1).
        """
        a = np.array(vec1)
        b = np.array(vec2)

        # If vectors are normalized, dot product = cosine similarity
        return float(np.dot(a, b))

    @staticmethod
    def find_similar(
        query_embedding: list[float],
        candidate_embeddings: list[list[float]],
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> list[tuple[int, float]]:
        """Find most similar embeddings to a query.

        Args:
            query_embedding: Query vector.
            candidate_embeddings: List of candidate vectors.
            top_k: Number of top results to return.
            threshold: Minimum similarity threshold.

        Returns:
            List of (index, similarity_score) tuples, sorted by similarity.
        """
        if not candidate_embeddings:
            return []

        query = np.array(query_embedding)
        candidates = np.array(candidate_embeddings)

        # Calculate similarities (assuming normalized vectors)
        similarities = np.dot(candidates, query)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append((int(idx), score))

        return results


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
