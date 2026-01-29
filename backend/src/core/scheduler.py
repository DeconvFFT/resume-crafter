"""Cron job scheduler for automated workflows.

Handles scheduling and execution of recurring automation tasks:
- Job discovery: Every 4 hours
- Job analysis: Every 1 hour
- Application queue processing: Continuous with configurable delays

Architecture:
    Scheduler → ARQ Background Workers → Database/Redis Updates → SSE Events

Usage:
    from src.core.scheduler import scheduler

    # Start the scheduler (typically in lifespan)
    await scheduler.start()

    # Stop the scheduler
    await scheduler.stop()

    # Get job status
    status = scheduler.get_job_status("job_discovery")
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine
from urllib.parse import urlparse

from arq import create_pool
from arq.connections import RedisSettings

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class CronJobStatus(str, Enum):
    """Status of a cron job."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    RUNNING = "running"


class CronJobType(str, Enum):
    """Types of cron jobs."""

    JOB_DISCOVERY = "job_discovery"
    JOB_ANALYSIS = "job_analysis"
    APPLICATION_QUEUE = "application_queue"


@dataclass
class CronJobState:
    """State tracking for a cron job."""

    job_type: CronJobType
    status: CronJobStatus = CronJobStatus.ACTIVE
    interval_seconds: int = 3600  # 1 hour default
    max_retries: int = 3
    retry_delay_seconds: int = 60

    # Runtime state
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    last_run_status: str | None = None
    last_run_duration_ms: int | None = None
    last_error: str | None = None
    run_count: int = 0
    error_count: int = 0
    consecutive_errors: int = 0

    # Internal
    _task: asyncio.Task | None = field(default=None, repr=False)
    _config: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "job_type": self.job_type.value,
            "status": self.status.value,
            "interval_seconds": self.interval_seconds,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_run_status": self.last_run_status,
            "last_run_duration_ms": self.last_run_duration_ms,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "config": self._config,
        }


def _get_redis_settings() -> RedisSettings:
    """Get Redis settings for ARQ from config."""
    url = str(settings.redis_url)
    parsed = urlparse(url)

    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0) if parsed.path else 0,
        password=parsed.password,
        username=parsed.username,
    )


class CronScheduler:
    """Scheduler for recurring automation jobs.

    Manages three main job types:
    1. Job Discovery - Searches for new jobs matching user campaigns (every 4 hours)
    2. Job Analysis - Analyzes discovered jobs for match scoring (every 1 hour)
    3. Application Queue - Processes pending applications (continuous with delays)

    Example:
        scheduler = CronScheduler()
        await scheduler.start()

        # Later...
        await scheduler.pause_job(CronJobType.JOB_DISCOVERY)
        await scheduler.resume_job(CronJobType.JOB_DISCOVERY)

        # Shutdown
        await scheduler.stop()
    """

    # Default intervals
    DEFAULT_JOB_DISCOVERY_INTERVAL = 4 * 60 * 60  # 4 hours
    DEFAULT_JOB_ANALYSIS_INTERVAL = 1 * 60 * 60  # 1 hour
    DEFAULT_APPLICATION_QUEUE_INTERVAL = 30  # 30 seconds between batches

    def __init__(self):
        """Initialize the scheduler."""
        self._jobs: dict[CronJobType, CronJobState] = {}
        self._running = False
        self._lock = asyncio.Lock()
        self._arq_pool = None

        # Initialize job states with default configurations
        self._jobs[CronJobType.JOB_DISCOVERY] = CronJobState(
            job_type=CronJobType.JOB_DISCOVERY,
            interval_seconds=self.DEFAULT_JOB_DISCOVERY_INTERVAL,
            _config={"batch_size": 100, "sources": ["linkedin", "greenhouse", "lever"]},
        )

        self._jobs[CronJobType.JOB_ANALYSIS] = CronJobState(
            job_type=CronJobType.JOB_ANALYSIS,
            interval_seconds=self.DEFAULT_JOB_ANALYSIS_INTERVAL,
            _config={"batch_size": 50, "min_match_score": 0.0},
        )

        self._jobs[CronJobType.APPLICATION_QUEUE] = CronJobState(
            job_type=CronJobType.APPLICATION_QUEUE,
            interval_seconds=self.DEFAULT_APPLICATION_QUEUE_INTERVAL,
            _config={"batch_size": 5, "delay_between_applications_seconds": 30},
        )

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    async def start(self) -> None:
        """Start the scheduler and all active jobs."""
        async with self._lock:
            if self._running:
                logger.warning("Scheduler is already running")
                return

            self._running = True
            logger.info("Starting cron scheduler...")

            for job_type, job_state in self._jobs.items():
                if job_state.status == CronJobStatus.ACTIVE:
                    await self._start_job(job_type)

            logger.info(f"Cron scheduler started with {len(self._jobs)} jobs configured")

    async def stop(self) -> None:
        """Stop the scheduler and all running jobs."""
        async with self._lock:
            if not self._running:
                return

            self._running = False
            logger.info("Stopping cron scheduler...")

            # Cancel all running tasks
            for job_type, job_state in self._jobs.items():
                if job_state._task and not job_state._task.done():
                    job_state._task.cancel()
                    try:
                        await job_state._task
                    except asyncio.CancelledError:
                        pass
                    job_state._task = None

            # Close ARQ pool
            if self._arq_pool:
                await self._arq_pool.close()
                self._arq_pool = None
                logger.info("Closed ARQ connection pool")

            logger.info("Cron scheduler stopped")

    async def _start_job(self, job_type: CronJobType) -> None:
        """Start a specific job's execution loop."""
        job_state = self._jobs[job_type]

        if job_state._task and not job_state._task.done():
            logger.warning(f"Job {job_type.value} is already running")
            return

        # Create the job task
        job_state._task = asyncio.create_task(
            self._job_loop(job_type),
            name=f"cron_{job_type.value}",
        )
        job_state.status = CronJobStatus.ACTIVE
        job_state.next_run_at = datetime.utcnow() + timedelta(seconds=job_state.interval_seconds)

        logger.info(
            f"Started job {job_type.value} with interval {job_state.interval_seconds}s, "
            f"next run at {job_state.next_run_at}"
        )

    async def _job_loop(self, job_type: CronJobType) -> None:
        """Main loop for executing a cron job."""
        job_state = self._jobs[job_type]

        # For application queue, run immediately then with delays
        # For discovery/analysis, wait for first interval
        if job_type == CronJobType.APPLICATION_QUEUE:
            initial_delay = 5  # Short initial delay
        else:
            initial_delay = job_state.interval_seconds

        await asyncio.sleep(initial_delay)

        while self._running and job_state.status in [CronJobStatus.ACTIVE, CronJobStatus.RUNNING]:
            try:
                job_state.status = CronJobStatus.RUNNING
                start_time = datetime.utcnow()

                logger.info(f"Running cron job: {job_type.value}")

                # Execute the job
                await self._execute_job(job_type)

                # Update success metrics
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                job_state.last_run_at = start_time
                job_state.last_run_status = "success"
                job_state.last_run_duration_ms = duration_ms
                job_state.run_count += 1
                job_state.consecutive_errors = 0
                job_state.status = CronJobStatus.ACTIVE
                job_state.next_run_at = datetime.utcnow() + timedelta(seconds=job_state.interval_seconds)

                logger.info(
                    f"Job {job_type.value} completed in {duration_ms}ms, "
                    f"next run at {job_state.next_run_at}"
                )

            except asyncio.CancelledError:
                logger.info(f"Job {job_type.value} was cancelled")
                raise

            except Exception as e:
                # Handle errors with retry logic
                job_state.error_count += 1
                job_state.consecutive_errors += 1
                job_state.last_run_status = "failed"
                job_state.last_error = str(e)
                job_state.status = CronJobStatus.ACTIVE

                logger.exception(f"Job {job_type.value} failed: {e}")

                # Exponential backoff for consecutive errors
                if job_state.consecutive_errors >= job_state.max_retries:
                    logger.error(
                        f"Job {job_type.value} has failed {job_state.consecutive_errors} "
                        f"times consecutively, pausing..."
                    )
                    job_state.status = CronJobStatus.PAUSED
                    return

                # Calculate retry delay with exponential backoff
                retry_delay = job_state.retry_delay_seconds * (2 ** (job_state.consecutive_errors - 1))
                retry_delay = min(retry_delay, job_state.interval_seconds)  # Cap at normal interval

                job_state.next_run_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                logger.info(f"Job {job_type.value} will retry in {retry_delay}s")

                await asyncio.sleep(retry_delay)
                continue

            # Wait for next interval
            await asyncio.sleep(job_state.interval_seconds)

    async def _get_arq_pool(self):
        """Get or create ARQ Redis connection pool."""
        if self._arq_pool is None:
            try:
                self._arq_pool = await create_pool(_get_redis_settings())
                logger.info("Created ARQ connection pool")
            except Exception as e:
                logger.error(f"Failed to create ARQ pool: {e}")
                raise
        return self._arq_pool

    async def _execute_job(self, job_type: CronJobType) -> None:
        """Execute the actual job logic by enqueuing ARQ tasks.

        This method dispatches to ARQ background workers for real execution.
        """
        try:
            pool = await self._get_arq_pool()
        except Exception as e:
            logger.error(f"Cannot execute job {job_type.value}: ARQ pool unavailable - {e}")
            raise

        if job_type == CronJobType.JOB_DISCOVERY:
            await self._run_job_discovery(pool)
        elif job_type == CronJobType.JOB_ANALYSIS:
            await self._run_job_analysis(pool)
        elif job_type == CronJobType.APPLICATION_QUEUE:
            await self._run_application_queue(pool)
        else:
            raise ValueError(f"Unknown job type: {job_type}")

    async def _run_job_discovery(self, pool) -> None:
        """Run job discovery for all active campaigns via ARQ worker.

        This discovers new jobs from configured sources (LinkedIn, Greenhouse, etc.)
        and stores them for analysis.
        """
        job_state = self._jobs[CronJobType.JOB_DISCOVERY]
        config = job_state._config

        logger.info(
            f"Enqueuing job discovery task with config: batch_size={config.get('batch_size')}, "
            f"sources={config.get('sources')}"
        )

        # Enqueue the actual ARQ task
        job = await pool.enqueue_job("run_scheduled_discovery")
        logger.info(f"Job discovery task enqueued: {job.job_id}")

    async def _run_job_analysis(self, pool) -> None:
        """Analyze discovered jobs for match scoring via ARQ worker.

        This processes unanalyzed jobs and calculates match scores
        based on user profiles and campaign criteria.
        """
        job_state = self._jobs[CronJobType.JOB_ANALYSIS]
        config = job_state._config

        logger.info(
            f"Enqueuing job analysis task with config: batch_size={config.get('batch_size')}, "
            f"min_match_score={config.get('min_match_score')}"
        )

        # Enqueue the actual ARQ task
        job = await pool.enqueue_job("run_scheduled_analysis")
        logger.info(f"Job analysis task enqueued: {job.job_id}")

    async def _run_application_queue(self, pool) -> None:
        """Process the application queue via ARQ worker.

        This handles pending applications by generating resumes,
        preparing application materials, and tracking status.
        """
        job_state = self._jobs[CronJobType.APPLICATION_QUEUE]
        config = job_state._config

        logger.info(
            f"Enqueuing application queue task with config: batch_size={config.get('batch_size')}, "
            f"delay={config.get('delay_between_applications_seconds')}s"
        )

        # Enqueue the actual ARQ task
        job = await pool.enqueue_job("run_scheduled_queue_processing")
        logger.info(f"Application queue task enqueued: {job.job_id}")

    # ============ Job Control Methods ============

    async def pause_job(self, job_type: CronJobType) -> CronJobState:
        """Pause a running job."""
        async with self._lock:
            job_state = self._jobs.get(job_type)
            if not job_state:
                raise ValueError(f"Unknown job type: {job_type}")

            if job_state._task and not job_state._task.done():
                job_state._task.cancel()
                try:
                    await job_state._task
                except asyncio.CancelledError:
                    pass
                job_state._task = None

            job_state.status = CronJobStatus.PAUSED
            job_state.next_run_at = None

            logger.info(f"Paused job: {job_type.value}")
            return job_state

    async def resume_job(self, job_type: CronJobType) -> CronJobState:
        """Resume a paused job."""
        async with self._lock:
            job_state = self._jobs.get(job_type)
            if not job_state:
                raise ValueError(f"Unknown job type: {job_type}")

            if job_state.status == CronJobStatus.PAUSED:
                job_state.consecutive_errors = 0  # Reset error count
                await self._start_job(job_type)

            logger.info(f"Resumed job: {job_type.value}")
            return job_state

    async def trigger_job(self, job_type: CronJobType) -> CronJobState:
        """Trigger immediate execution of a job."""
        job_state = self._jobs.get(job_type)
        if not job_state:
            raise ValueError(f"Unknown job type: {job_type}")

        logger.info(f"Manually triggering job: {job_type.value}")

        # Execute immediately in background
        asyncio.create_task(self._execute_job(job_type))

        return job_state

    def get_job_status(self, job_type: CronJobType) -> CronJobState | None:
        """Get the status of a specific job."""
        return self._jobs.get(job_type)

    def get_all_job_statuses(self) -> list[dict[str, Any]]:
        """Get the status of all jobs."""
        return [job_state.to_dict() for job_state in self._jobs.values()]

    async def update_job_config(
        self,
        job_type: CronJobType,
        interval_seconds: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> CronJobState:
        """Update job configuration."""
        async with self._lock:
            job_state = self._jobs.get(job_type)
            if not job_state:
                raise ValueError(f"Unknown job type: {job_type}")

            if interval_seconds is not None:
                if interval_seconds < 60:
                    raise ValueError("Minimum interval is 60 seconds")
                job_state.interval_seconds = interval_seconds

            if config is not None:
                job_state._config.update(config)

            logger.info(f"Updated config for job {job_type.value}")
            return job_state


# Global scheduler instance
scheduler = CronScheduler()


# ============ Convenience Functions ============


async def start_scheduler() -> None:
    """Start the global scheduler."""
    await scheduler.start()


async def stop_scheduler() -> None:
    """Stop the global scheduler."""
    await scheduler.stop()


def get_scheduler() -> CronScheduler:
    """Get the global scheduler instance."""
    return scheduler
