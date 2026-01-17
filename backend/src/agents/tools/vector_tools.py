"""Vector search tools for semantic matching.

Provides tools for searching similar content using embeddings.
"""

import logging
from uuid import UUID

from .registry import ToolRegistry, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


def register_vector_tools(registry: ToolRegistry) -> None:
    """Register vector search tools with the registry."""

    @registry.register(
        name="vector_search",
        description="Search for similar bullet points using semantic similarity",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="The text to find similar content for",
            ),
            ToolParameter(
                name="user_id",
                type="string",
                description="User ID to scope the search",
            ),
            ToolParameter(
                name="bullet_type",
                type="string",
                description="Type of bullets to search (experience, project, or all)",
                required=False,
                enum=["experience", "project", "all"],
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="Maximum number of results to return",
                required=False,
            ),
        ],
    )
    async def vector_search(
        query: str,
        user_id: str,
        bullet_type: str = "all",
        limit: int = 5,
    ) -> ToolResult:
        """Search for similar bullet points."""
        try:
            from src.storage.vector_store import get_vector_store
            from src.core.embeddings import get_embedding_service

            vector_store = get_vector_store()
            embedding_service = get_embedding_service()

            # Generate query embedding
            query_embedding = await embedding_service.embed_single(query)

            # Build filter
            where_filter = {"user_id": user_id}
            if bullet_type != "all":
                where_filter["type"] = bullet_type

            # Search
            results = await vector_store.search(
                query_embedding=query_embedding,
                n_results=limit,
                where=where_filter,
            )

            # Format results
            matches = []
            for i, (doc_id, content, metadata, distance) in enumerate(
                zip(
                    results.get("ids", [[]])[0],
                    results.get("documents", [[]])[0],
                    results.get("metadatas", [[]])[0],
                    results.get("distances", [[]])[0],
                )
            ):
                matches.append({
                    "id": doc_id,
                    "content": content,
                    "type": metadata.get("type", "unknown"),
                    "bullet_id": metadata.get("bullet_id"),
                    "document_id": metadata.get("document_id"),
                    "similarity": 1 - distance,  # Convert distance to similarity
                    "rank": i + 1,
                })

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "query": query,
                    "matches": matches,
                    "total_found": len(matches),
                },
            )

        except Exception as e:
            logger.exception(f"Vector search failed: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Vector search failed: {e}",
            )

    @registry.register(
        name="check_duplicate_content",
        description="Check if content already exists to prevent duplicates",
        parameters=[
            ToolParameter(
                name="content",
                type="string",
                description="The content to check for duplicates",
            ),
            ToolParameter(
                name="user_id",
                type="string",
                description="User ID to scope the search",
            ),
            ToolParameter(
                name="similarity_threshold",
                type="number",
                description="Similarity threshold (0-1) above which content is considered duplicate",
                required=False,
            ),
        ],
    )
    async def check_duplicate_content(
        content: str,
        user_id: str,
        similarity_threshold: float = 0.9,
    ) -> ToolResult:
        """Check if similar content already exists."""
        try:
            from src.storage.vector_store import get_vector_store
            from src.core.embeddings import get_embedding_service

            vector_store = get_vector_store()
            embedding_service = get_embedding_service()

            # Generate query embedding
            query_embedding = await embedding_service.embed_single(content)

            # Search for very similar content
            results = await vector_store.search(
                query_embedding=query_embedding,
                n_results=3,
                where={"user_id": user_id},
            )

            # Check for duplicates
            duplicates = []
            if results.get("distances"):
                for i, (doc_id, doc_content, metadata, distance) in enumerate(
                    zip(
                        results.get("ids", [[]])[0],
                        results.get("documents", [[]])[0],
                        results.get("metadatas", [[]])[0],
                        results.get("distances", [[]])[0],
                    )
                ):
                    similarity = 1 - distance
                    if similarity >= similarity_threshold:
                        duplicates.append({
                            "id": doc_id,
                            "content": doc_content,
                            "similarity": similarity,
                            "type": metadata.get("type"),
                        })

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "content": content[:100] + "..." if len(content) > 100 else content,
                    "is_duplicate": len(duplicates) > 0,
                    "duplicates": duplicates,
                    "threshold": similarity_threshold,
                },
            )

        except Exception as e:
            # If vector store unavailable, assume not duplicate
            logger.warning(f"Duplicate check failed (assuming not duplicate): {e}")
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "content": content[:100] + "..." if len(content) > 100 else content,
                    "is_duplicate": False,
                    "duplicates": [],
                    "threshold": similarity_threshold,
                    "warning": "Vector store unavailable, skipped duplicate check",
                },
            )
