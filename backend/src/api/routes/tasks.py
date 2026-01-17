"""Background task status routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.models.database import BackgroundTask
from src.models.schemas.common import TaskStatusResponse
from src.storage.database import get_db

router = APIRouter()


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BackgroundTask:
    """Get the status of a background task."""
    result = await db.execute(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return task


@router.get("/entity/{entity_id}", response_model=TaskStatusResponse | None)
async def get_task_by_entity(
    entity_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    task_type: str | None = None,
) -> BackgroundTask | None:
    """Get the most recent task for an entity (e.g., project, document).

    Args:
        entity_id: The ID of the entity (project, document, etc.)
        task_type: Optional filter by task type (e.g., 'enrich_project')
    """
    query = select(BackgroundTask).where(
        BackgroundTask.entity_id == entity_id,
        BackgroundTask.user_id == current_user.id,
    )

    if task_type:
        query = query.where(BackgroundTask.task_type == task_type)

    query = query.order_by(BackgroundTask.created_at.desc()).limit(1)

    result = await db.execute(query)
    task = result.scalar_one_or_none()

    return task
