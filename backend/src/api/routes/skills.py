"""Skills routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.models.database import Skill, SkillCategory, ProficiencyLevel
from src.models.schemas.skill import (
    BulkSkillCreate,
    SkillCreate,
    SkillListResponse,
    SkillResponse,
    SkillUpdate,
    SkillCategoryGroup,
)
from src.storage.database import get_db

router = APIRouter()


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    skill_data: SkillCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Skill:
    """Create a new skill."""
    skill = Skill(
        user_id=current_user.id,
        name=skill_data.name,
        category=SkillCategory(skill_data.category),
        proficiency=ProficiencyLevel(skill_data.proficiency) if skill_data.proficiency else None,
        years_of_experience=skill_data.years_of_experience,
        is_highlighted=skill_data.is_highlighted,
        display_order=skill_data.display_order,
    )
    db.add(skill)
    await db.flush()
    await db.refresh(skill)
    return skill


@router.post("/bulk", response_model=SkillListResponse, status_code=status.HTTP_201_CREATED)
async def create_skills_bulk(
    bulk_data: BulkSkillCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillListResponse:
    """Create multiple skills at once."""
    created_skills = []
    for skill_data in bulk_data.skills:
        skill = Skill(
            user_id=current_user.id,
            name=skill_data.name,
            category=SkillCategory(skill_data.category),
            proficiency=ProficiencyLevel(skill_data.proficiency) if skill_data.proficiency else None,
            years_of_experience=skill_data.years_of_experience,
            is_highlighted=skill_data.is_highlighted,
            display_order=skill_data.display_order,
        )
        db.add(skill)
        created_skills.append(skill)

    await db.flush()
    for skill in created_skills:
        await db.refresh(skill)

    return SkillListResponse(items=created_skills, total=len(created_skills))


@router.get("", response_model=SkillListResponse)
async def list_skills(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category: str | None = None,
) -> SkillListResponse:
    """List all skills for current user, optionally filtered by category."""
    query = select(Skill).where(
        Skill.user_id == current_user.id,
        Skill.deleted_at.is_(None),
    )

    if category:
        query = query.where(Skill.category == SkillCategory(category))

    query = query.order_by(Skill.display_order, Skill.name)
    result = await db.execute(query)
    skills = result.scalars().all()

    return SkillListResponse(items=list(skills), total=len(skills))


@router.get("/grouped", response_model=list[SkillCategoryGroup])
async def list_skills_grouped(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SkillCategoryGroup]:
    """List skills grouped by category."""
    result = await db.execute(
        select(Skill)
        .where(Skill.user_id == current_user.id, Skill.deleted_at.is_(None))
        .order_by(Skill.category, Skill.display_order, Skill.name)
    )
    skills = result.scalars().all()

    # Group by category
    groups: dict[str, list[Skill]] = {}
    for skill in skills:
        cat = skill.category.value
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(skill)

    return [
        SkillCategoryGroup(category=cat, skills=cat_skills)
        for cat, cat_skills in groups.items()
    ]


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Skill:
    """Get a specific skill."""
    result = await db.execute(
        select(Skill).where(
            Skill.id == skill_id,
            Skill.user_id == current_user.id,
            Skill.deleted_at.is_(None),
        )
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    return skill


@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: UUID,
    skill_data: SkillUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Skill:
    """Update a skill."""
    result = await db.execute(
        select(Skill).where(
            Skill.id == skill_id,
            Skill.user_id == current_user.id,
            Skill.deleted_at.is_(None),
        )
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    update_data = skill_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "category" and value:
            value = SkillCategory(value)
        elif field == "proficiency" and value:
            value = ProficiencyLevel(value)
        setattr(skill, field, value)

    await db.flush()
    await db.refresh(skill)

    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft delete a skill."""
    result = await db.execute(
        select(Skill).where(
            Skill.id == skill_id,
            Skill.user_id == current_user.id,
            Skill.deleted_at.is_(None),
        )
    )
    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    from datetime import datetime, timezone
    skill.deleted_at = datetime.now(timezone.utc)

    await db.flush()
