"""Resume matching and generation routes."""

import logging
from typing import Annotated
from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import CurrentUser
from src.models.database import BackgroundTask, JobDescription, ResumeMatch, ResumeMatchItem, TaskStatus, User
from src.core.resume_generator import get_resume_generator

logger = logging.getLogger(__name__)


async def get_arq_redis() -> ArqRedis:
    """Get ARQ Redis connection."""
    from arq import create_pool
    from src.tasks.worker import get_redis_settings
    return await create_pool(get_redis_settings())


from src.models.schemas.resume import (
    GeneratedResume,
    MatchItemResponse,
    MatchListResponse,
    MatchRequest,
    MatchResponse,
    ResumeGenerateRequest,
    ResumeGenerateResponse,
    ToggleMatchItemRequest,
)
from src.storage.database import get_db

router = APIRouter()


@router.post("/match", response_model=MatchResponse, status_code=status.HTTP_201_CREATED)
async def create_match(
    request: MatchRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchResponse:
    """Generate resume matches for a job description."""
    # Verify job exists and belongs to user
    job_result = await db.execute(
        select(JobDescription).where(
            JobDescription.id == request.job_id,
            JobDescription.user_id == current_user.id,
            JobDescription.deleted_at.is_(None),
        )
    )
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Create match record
    match = ResumeMatch(
        user_id=current_user.id,
        job_id=request.job_id,
        overall_match_score=0.0,
        skill_coverage=0.0,
        experience_relevance=0.0,
        processing_status=TaskStatus.PENDING,
    )
    db.add(match)
    await db.flush()

    # Create background task record for tracking
    task = BackgroundTask(
        user_id=current_user.id,
        task_type="generate_match",
        entity_id=match.id,
        status=TaskStatus.PENDING,
        progress=0,
    )
    db.add(task)
    await db.flush()

    # Enqueue background task for matching algorithm
    try:
        arq = await get_arq_redis()
        await arq.enqueue_job(
            "generate_match",
            match.id,
            current_user.id,
            request.max_experience_bullets,
            request.max_project_bullets,
        )
        await arq.close()
        logger.info(f"Enqueued match generation task for match {match.id}")
    except Exception as e:
        logger.warning(f"Failed to enqueue match generation: {e}")
        # Still return the match - can be retried later

    await db.refresh(match)

    # Build response manually to avoid lazy loading issues
    return MatchResponse(
        id=str(match.id),
        job_id=str(match.job_id),
        job_role=job.role,
        job_company=job.company,
        overall_match_score=match.overall_match_score,
        skill_coverage=match.skill_coverage,
        experience_relevance=match.experience_relevance,
        processing_status=match.processing_status.value,
        items=[],  # No items yet for new match
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


@router.get("/matches", response_model=MatchListResponse)
async def list_matches(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchListResponse:
    """List all resume matches for current user."""
    result = await db.execute(
        select(ResumeMatch)
        .options(selectinload(ResumeMatch.items), selectinload(ResumeMatch.job))
        .where(ResumeMatch.user_id == current_user.id, ResumeMatch.deleted_at.is_(None))
        .order_by(ResumeMatch.created_at.desc())
    )
    matches = result.scalars().all()

    # Build response manually to include job_role and job_company
    match_responses = []
    for match in matches:
        match_responses.append(MatchResponse(
            id=str(match.id),
            job_id=str(match.job_id),
            job_role=match.job.role if match.job else None,
            job_company=match.job.company if match.job else None,
            overall_match_score=match.overall_match_score,
            skill_coverage=match.skill_coverage,
            experience_relevance=match.experience_relevance,
            processing_status=match.processing_status.value,
            items=[],  # TODO: Convert items properly
            created_at=match.created_at,
            updated_at=match.updated_at,
        ))

    return MatchListResponse(items=match_responses, total=len(match_responses))


@router.get("/matches/{match_id}", response_model=MatchResponse)
async def get_match(
    match_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MatchResponse:
    """Get a specific match with all items."""
    result = await db.execute(
        select(ResumeMatch)
        .options(
            selectinload(ResumeMatch.items).selectinload(ResumeMatchItem.requirement),
            selectinload(ResumeMatch.items).selectinload(ResumeMatchItem.experience_bullet),
            selectinload(ResumeMatch.items).selectinload(ResumeMatchItem.project_bullet),
            selectinload(ResumeMatch.job),
        )
        .where(
            ResumeMatch.id == match_id,
            ResumeMatch.user_id == current_user.id,
            ResumeMatch.deleted_at.is_(None),
        )
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    # Convert items to response format
    item_responses = []
    for item in match.items:
        # Determine bullet source and content
        if item.experience_bullet:
            bullet_content = item.experience_bullet.content
            bullet_source = "experience"
        elif item.project_bullet:
            bullet_content = item.project_bullet.content
            bullet_source = "project"
        else:
            bullet_content = ""
            bullet_source = "experience"  # fallback

        item_responses.append(MatchItemResponse(
            id=str(item.id),
            requirement_id=str(item.requirement_id),
            requirement_content=item.requirement.content if item.requirement else "",
            experience_bullet_id=str(item.experience_bullet_id) if item.experience_bullet_id else None,
            project_bullet_id=str(item.project_bullet_id) if item.project_bullet_id else None,
            bullet_content=bullet_content,
            bullet_source=bullet_source,
            relevance_score=item.relevance_score,
            match_explanation=item.match_explanation,
            included_in_resume=item.included_in_resume,
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))

    return MatchResponse(
        id=str(match.id),
        job_id=str(match.job_id),
        job_role=match.job.role if match.job else None,
        job_company=match.job.company if match.job else None,
        overall_match_score=match.overall_match_score,
        skill_coverage=match.skill_coverage,
        experience_relevance=match.experience_relevance,
        processing_status=match.processing_status.value,
        items=item_responses,
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


@router.put("/matches/{match_id}/items/{item_id}")
async def toggle_match_item(
    match_id: UUID,
    item_id: UUID,
    request: ToggleMatchItemRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Toggle whether a match item is included in the resume."""
    # Verify match ownership
    match_result = await db.execute(
        select(ResumeMatch).where(
            ResumeMatch.id == match_id,
            ResumeMatch.user_id == current_user.id,
            ResumeMatch.deleted_at.is_(None),
        )
    )
    match = match_result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    # Update item
    item_result = await db.execute(
        select(ResumeMatchItem).where(
            ResumeMatchItem.id == item_id,
            ResumeMatchItem.match_id == match_id,
        )
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match item not found")

    item.included_in_resume = request.included
    await db.flush()

    return {"id": str(item_id), "included_in_resume": item.included_in_resume}


@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_match(
    match_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a resume match (soft delete)."""
    from datetime import datetime, timezone

    result = await db.execute(
        select(ResumeMatch).where(
            ResumeMatch.id == match_id,
            ResumeMatch.user_id == current_user.id,
            ResumeMatch.deleted_at.is_(None),
        )
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    # Soft delete the match
    match.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"Deleted match {match_id} for user {current_user.id}")


@router.post("/generate", response_model=ResumeGenerateResponse)
async def generate_resume(
    request: ResumeGenerateRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeGenerateResponse:
    """Generate final resume from match results."""
    # Get match with all related data
    result = await db.execute(
        select(ResumeMatch)
        .options(
            selectinload(ResumeMatch.items).selectinload(ResumeMatchItem.experience_bullet),
            selectinload(ResumeMatch.items).selectinload(ResumeMatchItem.project_bullet),
            selectinload(ResumeMatch.job),
        )
        .where(
            ResumeMatch.id == request.match_id,
            ResumeMatch.user_id == current_user.id,
            ResumeMatch.deleted_at.is_(None),
        )
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    # Get full User object (auth user lacks profile fields like websites)
    user_result = await db.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one()

    # Use ResumeGenerator to create the resume
    resume_gen = get_resume_generator()

    if request.format == "json":
        json_data = await resume_gen.generate_json(db, match, user)
        content = GeneratedResume(
            profile=json_data["profile"],
            experiences=json_data["experiences"],
            projects=json_data["projects"],
            skills=json_data["skills"],
        )
        return ResumeGenerateResponse(
            match_id=match.id,
            format=request.format,
            content=content,
        )
    elif request.format == "markdown":
        markdown_content = await resume_gen.generate_markdown(db, match, user)
        return ResumeGenerateResponse(
            match_id=match.id,
            format=request.format,
            content=markdown_content,
        )
    else:  # google_doc
        # Google Docs requires OAuth - defer for now
        return ResumeGenerateResponse(
            match_id=match.id,
            format=request.format,
            content="Google Doc generation requires OAuth authentication. Please use JSON or Markdown format.",
            google_doc_url=None,
        )
