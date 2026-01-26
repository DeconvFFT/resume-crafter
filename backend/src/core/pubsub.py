"""Redis Pub/Sub service for real-time event streaming.

Provides a bridge between ARQ background workers and SSE endpoints:
- Workers publish events to Redis channels
- SSE endpoints subscribe to channels and stream to clients

Architecture:
    ARQ Worker → Redis Pub/Sub → FastAPI SSE → Frontend EventSource
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator
from uuid import UUID

import redis.asyncio as redis
from pydantic import BaseModel

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EventType(str, Enum):
    """Types of events that can be published."""

    # Document processing events
    INIT = "init"
    LOG = "log"
    STATUS = "status"
    THINKING = "thinking"
    THINKING_COMPLETE = "thinking_complete"
    PROGRESS = "progress"
    DONE = "done"
    ERROR = "error"

    # Generic events
    HEARTBEAT = "heartbeat"


class DocumentEvent(BaseModel):
    """Event payload for document processing updates."""

    event_type: EventType
    document_id: str
    timestamp: str
    data: dict[str, Any] = {}

    def to_sse_data(self) -> str:
        """Format as SSE data payload."""
        return json.dumps(self.model_dump())


def _get_channel_name(document_id: UUID | str) -> str:
    """Get the Redis channel name for a document."""
    return f"document:{document_id}"


def _parse_redis_url() -> dict:
    """Parse Redis URL into connection parameters.

    Handles formats:
    - redis://localhost:6379/0
    - redis://default:password@host:port/0
    """
    from urllib.parse import urlparse

    url = str(settings.redis_url)
    parsed = urlparse(url)

    params = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 6379,
        "db": int(parsed.path.lstrip("/") or 0) if parsed.path else 0,
    }

    if parsed.password:
        params["password"] = parsed.password
    if parsed.username:
        params["username"] = parsed.username

    return params


class PubSubService:
    """Redis Pub/Sub service for real-time event streaming.

    Usage:
        # Publishing (from worker)
        async with PubSubService() as pubsub:
            await pubsub.publish_document_event(
                document_id=doc_id,
                event_type=EventType.LOG,
                data={"step": "classification", "message": "Analyzing..."}
            )

        # Subscribing (from SSE endpoint)
        async with PubSubService() as pubsub:
            async for event in pubsub.subscribe_document(document_id):
                yield f"data: {event.to_sse_data()}\n\n"
    """

    def __init__(self):
        """Initialize the Pub/Sub service."""
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._redis is None:
            params = _parse_redis_url()
            self._redis = redis.Redis(**params, decode_responses=True)
            logger.debug(f"Connected to Redis at {params['host']}:{params['port']}")

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.debug("Disconnected from Redis")

    async def __aenter__(self) -> "PubSubService":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def publish_document_event(
        self,
        document_id: UUID | str,
        event_type: EventType,
        data: dict[str, Any] | None = None,
    ) -> int:
        """Publish an event for a document.

        Args:
            document_id: The document ID.
            event_type: Type of event.
            data: Optional event data.

        Returns:
            Number of subscribers that received the message.
        """
        if self._redis is None:
            raise RuntimeError("PubSubService not connected")

        event = DocumentEvent(
            event_type=event_type,
            document_id=str(document_id),
            timestamp=datetime.utcnow().isoformat(),
            data=data or {},
        )

        channel = _get_channel_name(document_id)
        message = event.to_sse_data()

        num_subscribers = await self._redis.publish(channel, message)
        logger.debug(
            f"Published {event_type.value} to {channel} "
            f"({num_subscribers} subscribers)"
        )
        return num_subscribers

    async def subscribe_document(
        self,
        document_id: UUID | str,
        timeout: float = 300.0,
        heartbeat_interval: float = 15.0,
    ) -> AsyncGenerator[DocumentEvent, None]:
        """Subscribe to events for a document.

        Yields events as they arrive. Includes periodic heartbeats to keep
        the SSE connection alive.

        Args:
            document_id: The document ID to subscribe to.
            timeout: Total subscription timeout in seconds.
            heartbeat_interval: Interval between heartbeats in seconds.

        Yields:
            DocumentEvent objects as they arrive.
        """
        if self._redis is None:
            raise RuntimeError("PubSubService not connected")

        channel = _get_channel_name(document_id)
        self._pubsub = self._redis.pubsub()

        try:
            await self._pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")

            start_time = asyncio.get_event_loop().time()
            last_heartbeat = start_time

            while True:
                # Check timeout
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > timeout:
                    logger.info(f"Subscription timeout reached for {channel}")
                    break

                # Send heartbeat if needed
                if current_time - last_heartbeat > heartbeat_interval:
                    yield DocumentEvent(
                        event_type=EventType.HEARTBEAT,
                        document_id=str(document_id),
                        timestamp=datetime.utcnow().isoformat(),
                    )
                    last_heartbeat = current_time

                # Get message with short timeout to allow heartbeats
                try:
                    message = await asyncio.wait_for(
                        self._pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                if message is None:
                    continue

                if message["type"] != "message":
                    continue

                try:
                    data = json.loads(message["data"])
                    event = DocumentEvent(**data)
                    yield event

                    # Stop subscription on done or error
                    if event.event_type in (EventType.DONE, EventType.ERROR):
                        logger.info(f"Ending subscription for {channel} on {event.event_type.value}")
                        break

                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Invalid message on {channel}: {e}")
                    continue

        finally:
            await self._pubsub.unsubscribe(channel)
            logger.info(f"Unsubscribed from channel: {channel}")


# Global instance for worker (singleton pattern)
_worker_pubsub: PubSubService | None = None


async def get_worker_pubsub() -> PubSubService:
    """Get or create a global PubSubService instance for workers.

    This provides a shared connection for workers to publish events.
    """
    global _worker_pubsub
    if _worker_pubsub is None:
        _worker_pubsub = PubSubService()
        await _worker_pubsub.connect()
    return _worker_pubsub


async def close_worker_pubsub() -> None:
    """Close the global worker PubSubService instance."""
    global _worker_pubsub
    if _worker_pubsub is not None:
        await _worker_pubsub.disconnect()
        _worker_pubsub = None


@asynccontextmanager
async def pubsub_context() -> AsyncGenerator[PubSubService, None]:
    """Context manager for temporary PubSub connections (SSE endpoints)."""
    pubsub = PubSubService()
    try:
        await pubsub.connect()
        yield pubsub
    finally:
        await pubsub.disconnect()


# Convenience functions for publishing from workers
async def publish_log(
    document_id: UUID | str,
    step: str,
    status: str,
    message: str,
    details: dict | None = None,
) -> None:
    """Publish a log event for document processing.

    Args:
        document_id: The document ID.
        step: Processing step name.
        status: Step status (started, completed, failed, thinking).
        message: Human-readable message.
        details: Optional additional details.
    """
    pubsub = await get_worker_pubsub()
    await pubsub.publish_document_event(
        document_id=document_id,
        event_type=EventType.LOG,
        data={
            "step": step,
            "status": status,
            "message": message,
            "details": details or {},
        },
    )


async def publish_thinking(
    document_id: UUID | str,
    thinking_text: str,
    is_complete: bool = False,
) -> None:
    """Publish Chain-of-Thought thinking event.

    Args:
        document_id: The document ID.
        thinking_text: The LLM's reasoning/thinking text.
        is_complete: Whether this is the final thinking chunk.
    """
    pubsub = await get_worker_pubsub()
    event_type = EventType.THINKING_COMPLETE if is_complete else EventType.THINKING
    await pubsub.publish_document_event(
        document_id=document_id,
        event_type=event_type,
        data={"thinking": thinking_text},
    )


async def publish_status(
    document_id: UUID | str,
    status: str,
    progress: int | None = None,
) -> None:
    """Publish status change event.

    Args:
        document_id: The document ID.
        status: New status (processing, completed, failed).
        progress: Optional progress percentage (0-100).
    """
    pubsub = await get_worker_pubsub()
    data = {"status": status}
    if progress is not None:
        data["progress"] = progress

    await pubsub.publish_document_event(
        document_id=document_id,
        event_type=EventType.STATUS,
        data=data,
    )


async def publish_done(
    document_id: UUID | str,
    result: dict | None = None,
) -> None:
    """Publish completion event.

    Args:
        document_id: The document ID.
        result: Optional result data.
    """
    pubsub = await get_worker_pubsub()
    await pubsub.publish_document_event(
        document_id=document_id,
        event_type=EventType.DONE,
        data=result or {},
    )


async def publish_error(
    document_id: UUID | str,
    error: str,
    step: str | None = None,
) -> None:
    """Publish error event.

    Args:
        document_id: The document ID.
        error: Error message.
        step: Optional step where error occurred.
    """
    pubsub = await get_worker_pubsub()
    data = {"error": error}
    if step:
        data["step"] = step

    await pubsub.publish_document_event(
        document_id=document_id,
        event_type=EventType.ERROR,
        data=data,
    )
