"""Profile routes."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.models.database import User
from src.models.schemas.profile import ProfileResponse, ProfileUpdate
from src.storage.database import get_db

router = APIRouter()


@router.get("", response_model=ProfileResponse)
async def get_profile(current_user: CurrentUser) -> User:
    """Get current user's profile."""
    return current_user


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Update current user's profile."""
    update_data = profile_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    await db.refresh(current_user)

    return current_user
