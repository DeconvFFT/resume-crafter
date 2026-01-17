"""Server-Sent Events (SSE) endpoints for real-time streaming.

Provides real-time updates for document processing using SSE. Replaces
polling with push-based updates for better UX and reduced server load.

Usage:
    const eventSource = new EventSource('/sse/documents/{id}/stream', {
        headers: { Authorization: `Bearer ${token}` }
    });

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.event_type, data.data);
    };
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import get_current_user
from src.auth.dependencies import get_user_from_token_query
from src.core.pubsub import EventType, pubsub_context, DocumentEvent
from src.models.database import Document, User
from src.storage.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


async def _verify_document_access(
    document_id: UUID,
    user: User,
    db: AsyncSession,
) -> Document:
    """Verify user has access to the document.

    Args:
        document_id: The document ID.
        user: The authenticated user.
        db: Database session.

    Returns:
        The document if access is granted.

    Raises:
        HTTPException: If document not found or access denied.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user.id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


async def _generate_sse_stream(
    document_id: UUID,
    document: Document,
    include_history: bool = True,
):
    """Generate SSE stream for document processing.

    Args:
        document_id: The document ID.
        document: The document model.
        include_history: Whether to include existing logs on connect.

    Yields:
        SSE formatted strings.
    """
    # Send initial state with existing logs if requested
    if include_history and document.processing_logs:
        init_event = DocumentEvent(
            event_type=EventType.INIT,
            document_id=str(document_id),
            timestamp=document.updated_at.isoformat() if document.updated_at else "",
            data={
                "status": document.processing_status.value if document.processing_status else "pending",
                "logs": document.processing_logs,
            },
        )
        yield f"data: {init_event.to_sse_data()}\n\n"

    # If already completed or failed, send done event and close
    if document.processing_status and document.processing_status.value in ("completed", "failed"):
        done_event = DocumentEvent(
            event_type=EventType.DONE if document.processing_status.value == "completed" else EventType.ERROR,
            document_id=str(document_id),
            timestamp=document.updated_at.isoformat() if document.updated_at else "",
            data={
                "status": document.processing_status.value,
                "error": document.processing_error if document.processing_status.value == "failed" else None,
            },
        )
        yield f"data: {done_event.to_sse_data()}\n\n"
        return

    # Subscribe to real-time events via Redis Pub/Sub
    try:
        async with pubsub_context() as pubsub:
            async for event in pubsub.subscribe_document(document_id):
                yield f"data: {event.to_sse_data()}\n\n"

                # Stop on terminal events
                if event.event_type in (EventType.DONE, EventType.ERROR):
                    break

    except Exception as e:
        logger.exception(f"SSE stream error for document {document_id}: {e}")
        error_event = DocumentEvent(
            event_type=EventType.ERROR,
            document_id=str(document_id),
            timestamp="",
            data={"error": "Stream connection error", "detail": str(e)},
        )
        yield f"data: {error_event.to_sse_data()}\n\n"


@router.get(
    "/documents/{document_id}/stream",
    response_class=StreamingResponse,
    summary="Stream document processing events",
    description="""
    Stream real-time processing events for a document using Server-Sent Events (SSE).

    **Event Types:**
    - `init`: Initial state with existing logs (sent on connect)
    - `log`: Processing step log entry
    - `status`: Status change (processing/completed/failed)
    - `thinking`: Real-time LLM reasoning (Chain of Thought)
    - `thinking_complete`: LLM reasoning complete
    - `progress`: Progress percentage update
    - `done`: Processing complete
    - `error`: Processing failed
    - `heartbeat`: Keep-alive (every 15s)

    **Usage (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/sse/documents/{id}/stream');

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch (data.event_type) {
            case 'log':
                console.log(data.data.message);
                break;
            case 'thinking':
                // Display real-time LLM reasoning
                appendThinking(data.data.thinking);
                break;
            case 'done':
                eventSource.close();
                break;
        }
    };
    ```
    """,
    responses={
        200: {
            "description": "SSE stream of document events",
            "content": {"text/event-stream": {}},
        },
        404: {"description": "Document not found"},
    },
)
async def stream_document_events(
    document_id: UUID,
    include_history: bool = Query(
        default=True,
        description="Include existing processing logs on connect",
    ),
    token: str | None = Query(
        default=None,
        description="JWT access token (for SSE clients that can't send headers)",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Stream document processing events via SSE.

    This endpoint provides real-time updates as a document is processed,
    including LLM reasoning (Chain of Thought) for transparency.

    Note: EventSource doesn't support custom headers, so we accept the
    access token as a query parameter for SSE clients.

    Args:
        document_id: The document ID to stream.
        include_history: Whether to include existing logs on connect.
        token: JWT access token (for clients that can't send headers).
        db: Database session.

    Returns:
        StreamingResponse with SSE content type.
    """
    # Authenticate via query parameter token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required for SSE streaming",
        )

    current_user = await get_user_from_token_query(token, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    document = await _verify_document_access(document_id, current_user, db)

    return StreamingResponse(
        _generate_sse_stream(document_id, document, include_history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/health",
    summary="SSE health check",
    responses={200: {"description": "SSE service is healthy"}},
)
async def sse_health():
    """Check if SSE service (Redis Pub/Sub) is available."""
    try:
        async with pubsub_context() as pubsub:
            # Simple connectivity check
            return {"status": "healthy", "service": "sse"}
    except Exception as e:
        logger.error(f"SSE health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"SSE service unavailable: {str(e)}",
        )
