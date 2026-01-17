"""Graceful shutdown infrastructure for ARQ workers.

This module is separate from worker.py to avoid circular imports,
as document_tasks.py needs these functions but worker.py imports
document_tasks.py for task registration.
"""

import asyncio
import logging
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.tasks.checkpoint import CheckpointManager

logger = logging.getLogger(__name__)

# Global shutdown flag - set when SIGTERM/SIGINT received
_shutdown_requested = asyncio.Event()

# Registry of active checkpoint managers - allows notifying running tasks
_active_checkpoint_managers: dict[UUID, "CheckpointManager"] = {}


def register_checkpoint_manager(document_id: UUID, manager: "CheckpointManager") -> None:
    """Register a checkpoint manager for graceful shutdown notification.

    Called when a task starts processing a document.
    """
    _active_checkpoint_managers[document_id] = manager
    logger.debug(f"Registered checkpoint manager for document {document_id}")


def unregister_checkpoint_manager(document_id: UUID) -> None:
    """Unregister a checkpoint manager after task completion.

    Called when a task finishes (success or failure).
    """
    _active_checkpoint_managers.pop(document_id, None)
    logger.debug(f"Unregistered checkpoint manager for document {document_id}")


def is_shutdown_requested() -> bool:
    """Check if a shutdown has been requested.

    Tasks should check this periodically and save state if True.
    """
    return _shutdown_requested.is_set()


def request_shutdown() -> None:
    """Signal that shutdown has been requested.

    Called by signal handlers in the worker.
    """
    _shutdown_requested.set()


def get_active_managers() -> dict[UUID, "CheckpointManager"]:
    """Get all active checkpoint managers.

    Used by shutdown handlers to notify running tasks.
    """
    return _active_checkpoint_managers.copy()


async def notify_all_managers_shutdown() -> None:
    """Notify all active checkpoint managers of pending shutdown.

    Gives tasks a chance to save their state before worker terminates.
    """
    for doc_id, manager in _active_checkpoint_managers.items():
        logger.info(f"Notifying task for document {doc_id} of pending shutdown")
        manager.shutdown_requested = True
