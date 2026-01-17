"""ChromaDB vector store for semantic search."""

import logging
from typing import Any

import chromadb
from chromadb.config import Settings

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStore:
    """ChromaDB-based vector store for embeddings."""

    def __init__(self):
        """Initialize ChromaDB client and collection."""
        self._client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection_name = settings.chroma_collection
        self._collection = None

    def _get_collection(self):
        """Get or create the collection."""
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )
        return self._collection

    async def add(
        self,
        id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        document: str | None = None,
    ) -> None:
        """Add a single embedding to the store.

        Args:
            id: Unique identifier for the embedding.
            embedding: The embedding vector.
            metadata: Optional metadata dict.
            document: Optional source document text.
        """
        collection = self._get_collection()
        collection.add(
            ids=[id],
            embeddings=[embedding],
            metadatas=[metadata] if metadata else None,
            documents=[document] if document else None,
        )
        logger.debug(f"Added embedding {id} to vector store")

    async def add_batch(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        """Add multiple embeddings to the store.

        Args:
            ids: List of unique identifiers.
            embeddings: List of embedding vectors.
            metadatas: Optional list of metadata dicts.
            documents: Optional list of source document texts.
        """
        if not ids:
            return

        collection = self._get_collection()
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        logger.debug(f"Added {len(ids)} embeddings to vector store")

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
    ) -> dict:
        """Query for similar embeddings.

        Args:
            query_embedding: The query vector.
            n_results: Number of results to return.
            where: Optional metadata filter.
            where_document: Optional document content filter.

        Returns:
            Dict with ids, distances, metadatas, and documents.
        """
        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["distances", "metadatas", "documents"],
        )
        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
        }

    async def query_by_user(
        self,
        query_embedding: list[float],
        user_id: str,
        n_results: int = 10,
        bullet_type: str | None = None,
    ) -> dict:
        """Query for similar embeddings filtered by user.

        Args:
            query_embedding: The query vector.
            user_id: User ID to filter by.
            n_results: Number of results to return.
            bullet_type: Optional type filter (experience_bullet, project_bullet).

        Returns:
            Dict with ids, distances, metadatas, and documents.
        """
        where_filter = {"user_id": user_id}
        if bullet_type:
            where_filter["type"] = bullet_type

        return await self.query(
            query_embedding=query_embedding,
            n_results=n_results,
            where=where_filter,
        )

    async def get(self, id: str) -> dict | None:
        """Get a specific embedding by ID.

        Args:
            id: The embedding ID.

        Returns:
            Dict with embedding data or None if not found.
        """
        collection = self._get_collection()
        result = collection.get(
            ids=[id],
            include=["embeddings", "metadatas", "documents"],
        )
        if result["ids"]:
            return {
                "id": result["ids"][0],
                "embedding": result["embeddings"][0] if result["embeddings"] else None,
                "metadata": result["metadatas"][0] if result["metadatas"] else None,
                "document": result["documents"][0] if result["documents"] else None,
            }
        return None

    async def delete(self, id: str) -> None:
        """Delete an embedding by ID.

        Args:
            id: The embedding ID to delete.
        """
        collection = self._get_collection()
        collection.delete(ids=[id])
        logger.debug(f"Deleted embedding {id} from vector store")

    async def delete_by_user(self, user_id: str) -> None:
        """Delete all embeddings for a user.

        Args:
            user_id: User ID whose embeddings to delete.
        """
        collection = self._get_collection()
        collection.delete(where={"user_id": user_id})
        logger.info(f"Deleted all embeddings for user {user_id}")

    async def update_metadata(
        self,
        id: str,
        metadata: dict[str, Any],
    ) -> None:
        """Update metadata for an embedding.

        Args:
            id: The embedding ID.
            metadata: New metadata dict.
        """
        collection = self._get_collection()
        collection.update(ids=[id], metadatas=[metadata])

    def count(self) -> int:
        """Get total number of embeddings in the store.

        Returns:
            Number of embeddings.
        """
        collection = self._get_collection()
        return collection.count()

    def reset(self) -> None:
        """Delete and recreate the collection (use with caution)."""
        self._client.delete_collection(self._collection_name)
        self._collection = None
        self._get_collection()
        logger.warning(f"Reset vector store collection: {self._collection_name}")


# Singleton instance
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get or create the vector store singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
