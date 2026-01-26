"""ARQ background worker configuration with graceful shutdown support.

Provides checkpoint-aware shutdown handling so long-running tasks can save
their state before the worker terminates.
"""

import asyncio
import logging
import signal
from datetime import timedelta

from arq import cron
from arq.connections import RedisSettings

from src.config import get_settings
from src.tasks.shutdown import (
    request_shutdown,
    get_active_managers,
    notify_all_managers_shutdown,
    _shutdown_requested,
    _active_checkpoint_managers,
)

logger = logging.getLogger(__name__)
settings = get_settings()


async def _handle_shutdown_signal() -> None:
    """Handle SIGTERM/SIGINT by notifying all active tasks to save state.

    This is called when the worker receives a termination signal.
    It sets the global shutdown flag and notifies all active checkpoint
    managers so they can save their progress.
    """
    active_managers = get_active_managers()
    logger.warning(
        f"Shutdown signal received - notifying {len(active_managers)} active tasks"
    )
    request_shutdown()
    await notify_all_managers_shutdown()


def get_redis_settings() -> RedisSettings:
    """Get Redis settings for ARQ.

    Handles formats:
    - redis://localhost:6379/0
    - redis://default:password@host:port/0
    """
    from urllib.parse import urlparse

    url = str(settings.redis_url)
    parsed = urlparse(url)

    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0) if parsed.path else 0,
        password=parsed.password,
        username=parsed.username,
    )


async def startup(ctx: dict) -> None:
    """Worker startup handler with signal handling setup."""
    logger.info("ARQ worker starting up...")

    # Set up signal handlers for graceful shutdown
    # Note: ARQ handles some signals itself, but we add our custom handler
    # to notify checkpoint managers before ARQ's handler kicks in
    loop = asyncio.get_running_loop()

    def signal_handler(sig: signal.Signals) -> None:
        """Sync wrapper that schedules the async handler."""
        logger.info(f"Received signal {sig.name}")
        asyncio.create_task(_handle_shutdown_signal())

    # Register handlers for termination signals
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
            logger.debug(f"Registered signal handler for {sig.name}")
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            logger.warning(f"Could not add signal handler for {sig.name} (not supported)")

    # Reset shutdown flag (in case worker is restarted)
    _shutdown_requested.clear()

    # Initialize database connection
    from src.storage.database import AsyncSessionLocal

    ctx["db_session_factory"] = AsyncSessionLocal

    # Initialize services
    from src.core.embeddings import get_embedding_service

    ctx["embedding_service"] = get_embedding_service()

    # Initialize vector store (ChromaDB)
    from src.storage.vector_store import get_vector_store

    try:
        vector_store = get_vector_store()
        # Test connection by getting count
        vector_store.count()
        ctx["vector_store"] = vector_store
        logger.info("ChromaDB vector store connected")
    except Exception as e:
        logger.warning(f"ChromaDB unavailable, will operate without vector search: {e}")
        ctx["vector_store"] = None

    # Initialize Redis Pub/Sub for real-time event streaming
    from src.core.pubsub import get_worker_pubsub

    try:
        await get_worker_pubsub()
        logger.info("Redis Pub/Sub connected for event streaming")
    except Exception as e:
        logger.warning(f"Redis Pub/Sub unavailable, SSE streaming disabled: {e}")

    logger.info("ARQ worker ready")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown handler with checkpoint wait."""
    logger.info("ARQ worker shutting down...")

    # Give active tasks a moment to save their checkpoints
    if _active_checkpoint_managers:
        logger.info(
            f"Waiting for {len(_active_checkpoint_managers)} tasks to save checkpoints..."
        )
        # Wait up to 5 seconds for tasks to checkpoint
        await asyncio.sleep(2)

        # Check if any managers are still active
        remaining = len(_active_checkpoint_managers)
        if remaining > 0:
            logger.warning(f"{remaining} tasks did not complete checkpoint save")

    # Close Redis Pub/Sub connection
    try:
        from src.core.pubsub import close_worker_pubsub

        await close_worker_pubsub()
        logger.info("Redis Pub/Sub connection closed")
    except Exception as e:
        logger.warning(f"Error closing Redis Pub/Sub: {e}")

    # Close database connections
    try:
        from src.storage.database import close_db

        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")

    logger.info("ARQ worker shutdown complete")


# Import task functions
from src.tasks.document_tasks import process_document
from src.tasks.job_tasks import analyze_job
from src.tasks.matching_tasks import generate_match
from src.tasks.project_enrichment_tasks import enrich_project_from_github

# Import automation task functions
from src.tasks.automation_tasks import (
    discover_jobs,
    analyze_discovered_job,
    batch_analyze_jobs,
    process_application_queue,
    research_company,
    generate_outreach,
    batch_generate_outreach,
    run_scheduled_discovery,
    run_scheduled_analysis,
    run_scheduled_queue_processing,
)


class WorkerSettings:
    """ARQ worker settings."""

    redis_settings = get_redis_settings()

    # Task functions
    functions = [
        # Document processing tasks
        process_document,
        analyze_job,
        generate_match,
        enrich_project_from_github,
        # Automation tasks
        discover_jobs,
        analyze_discovered_job,
        batch_analyze_jobs,
        process_application_queue,
        research_company,
        generate_outreach,
        batch_generate_outreach,
        # Scheduled cron tasks (can also be called manually)
        run_scheduled_discovery,
        run_scheduled_analysis,
        run_scheduled_queue_processing,
    ]

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Worker configuration
    max_jobs = 10
    job_timeout = timedelta(minutes=30)  # Increased for LLM processing
    keep_result = timedelta(hours=24)
    poll_delay = 0.5

    # Retry configuration
    max_tries = 3
    retry_jobs = True

    # Cron jobs for periodic automation
    cron_jobs = [
        # Job discovery - runs every 6 hours
        cron(run_scheduled_discovery, hour={0, 6, 12, 18}, minute=0),
        # Job analysis - runs every 2 hours
        cron(run_scheduled_analysis, hour=None, minute=30),
        # Application queue processing - runs every 30 minutes during business hours
        cron(run_scheduled_queue_processing, hour={9, 10, 11, 12, 13, 14, 15, 16, 17}, minute={0, 30}),
    ]
