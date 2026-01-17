"""Job description routes."""

import logging
from typing import Annotated
from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import CurrentUser
from src.models.database import BackgroundTask, JobDescription, TaskStatus
from src.models.schemas.job import JobAnalysisRequest, JobListResponse, JobResponse
from src.storage.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_arq_redis() -> ArqRedis:
    """Get ARQ Redis connection."""
    from arq import create_pool
    from src.tasks.worker import get_redis_settings
    return await create_pool(get_redis_settings())


@router.post("/analyze", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def analyze_job_endpoint(
    request: JobAnalysisRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobDescription:
    """Analyze a job description from URL or raw text."""
    # Validate that at least one input is provided
    if not request.source_url and not request.raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either source_url or raw_text must be provided",
        )

    job = JobDescription(
        user_id=current_user.id,
        source_url=request.source_url,
        raw_text=request.raw_text or "",
        processing_status=TaskStatus.PENDING,
    )
    db.add(job)
    await db.flush()

    # Create background task record for tracking
    task = BackgroundTask(
        user_id=current_user.id,
        task_type="analyze_job",
        entity_id=job.id,
        status=TaskStatus.PENDING,
        progress=0,
    )
    db.add(task)
    await db.flush()

    # Enqueue background task for LLM analysis
    try:
        arq = await get_arq_redis()
        await arq.enqueue_job("analyze_job", job.id, current_user.id)
        await arq.close()
        logger.info(f"Enqueued job analysis task for job {job.id}")
    except Exception as e:
        logger.warning(f"Failed to enqueue job analysis: {e}")
        # Still return the job - can be retried later

    await db.refresh(job, ["requirements"])
    return job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobListResponse:
    """List all job descriptions for current user."""
    result = await db.execute(
        select(JobDescription)
        .options(selectinload(JobDescription.requirements))
        .where(JobDescription.user_id == current_user.id, JobDescription.deleted_at.is_(None))
        .order_by(JobDescription.created_at.desc())
    )
    jobs = result.scalars().all()

    return JobListResponse(items=list(jobs), total=len(jobs))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobDescription:
    """Get a specific job description with requirements."""
    result = await db.execute(
        select(JobDescription)
        .options(selectinload(JobDescription.requirements))
        .where(
            JobDescription.id == job_id,
            JobDescription.user_id == current_user.id,
            JobDescription.deleted_at.is_(None),
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft delete a job description."""
    result = await db.execute(
        select(JobDescription).where(
            JobDescription.id == job_id,
            JobDescription.user_id == current_user.id,
            JobDescription.deleted_at.is_(None),
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    from datetime import datetime, timezone
    job.deleted_at = datetime.now(timezone.utc)

    await db.flush()
