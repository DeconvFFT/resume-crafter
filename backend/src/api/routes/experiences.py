"""Experience routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import CurrentUser
from src.models.database import Experience, ExperienceBullet, SupportingDocument
from src.models.schemas.experience import (
    BulletCreate,
    BulletResponse,
    BulletUpdate,
    ExperienceCreate,
    ExperienceListResponse,
    ExperienceResponse,
    ExperienceUpdate,
)
from src.models.schemas.project import SupportingDocCreate, SupportingDocResponse
from src.storage.database import get_db

router = APIRouter()


@router.post("", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
async def create_experience(
    experience_data: ExperienceCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Experience:
    """Create a new experience entry."""
    experience = Experience(
        user_id=current_user.id,
        company=experience_data.company,
        role=experience_data.role,
        location=experience_data.location,
        start_date=experience_data.start_date,
        end_date=experience_data.end_date,
        is_current=experience_data.is_current,
    )

    # Add bullets
    for idx, bullet_data in enumerate(experience_data.bullets):
        bullet = ExperienceBullet(
            content=bullet_data.content,
            order_index=bullet_data.order_index or idx,
        )
        experience.bullets.append(bullet)

    db.add(experience)
    await db.flush()
    await db.refresh(experience, ["bullets"])

    return experience


@router.get("", response_model=ExperienceListResponse)
async def list_experiences(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperienceListResponse:
    """List all experiences for current user."""
    result = await db.execute(
        select(Experience)
        .options(selectinload(Experience.bullets))
        .where(Experience.user_id == current_user.id, Experience.deleted_at.is_(None))
        .order_by(Experience.start_date.desc())
    )
    experiences = result.scalars().all()

    return ExperienceListResponse(items=list(experiences), total=len(experiences))


@router.get("/{experience_id}", response_model=ExperienceResponse)
async def get_experience(
    experience_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Experience:
    """Get a specific experience."""
    result = await db.execute(
        select(Experience)
        .options(selectinload(Experience.bullets))
        .where(
            Experience.id == experience_id,
            Experience.user_id == current_user.id,
            Experience.deleted_at.is_(None),
        )
    )
    experience = result.scalar_one_or_none()

    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    return experience


@router.patch("/{experience_id}", response_model=ExperienceResponse)
async def update_experience(
    experience_id: UUID,
    experience_data: ExperienceUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Experience:
    """Update an experience entry."""
    result = await db.execute(
        select(Experience)
        .options(selectinload(Experience.bullets))
        .where(
            Experience.id == experience_id,
            Experience.user_id == current_user.id,
            Experience.deleted_at.is_(None),
        )
    )
    experience = result.scalar_one_or_none()

    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    update_data = experience_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(experience, field, value)

    await db.flush()
    await db.refresh(experience, ["bullets"])

    return experience


@router.delete("/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(
    experience_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft delete an experience."""
    result = await db.execute(
        select(Experience).where(
            Experience.id == experience_id,
            Experience.user_id == current_user.id,
            Experience.deleted_at.is_(None),
        )
    )
    experience = result.scalar_one_or_none()

    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    from datetime import datetime, timezone
    experience.deleted_at = datetime.now(timezone.utc)

    await db.flush()


# Bullet endpoints
@router.post("/{experience_id}/bullets", response_model=BulletResponse, status_code=status.HTTP_201_CREATED)
async def add_bullet(
    experience_id: UUID,
    bullet_data: BulletCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperienceBullet:
    """Add a bullet to an experience."""
    result = await db.execute(
        select(Experience).where(
            Experience.id == experience_id,
            Experience.user_id == current_user.id,
            Experience.deleted_at.is_(None),
        )
    )
    experience = result.scalar_one_or_none()

    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    bullet = ExperienceBullet(
        experience_id=experience_id,
        content=bullet_data.content,
        order_index=bullet_data.order_index,
    )

    db.add(bullet)
    await db.flush()
    await db.refresh(bullet)

    return bullet


@router.patch("/{experience_id}/bullets/{bullet_id}", response_model=BulletResponse)
async def update_bullet(
    experience_id: UUID,
    bullet_id: UUID,
    bullet_data: BulletUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExperienceBullet:
    """Update a bullet."""
    # Verify experience ownership
    exp_result = await db.execute(
        select(Experience).where(
            Experience.id == experience_id,
            Experience.user_id == current_user.id,
            Experience.deleted_at.is_(None),
        )
    )
    if not exp_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    result = await db.execute(
        select(ExperienceBullet).where(
            ExperienceBullet.id == bullet_id,
            ExperienceBullet.experience_id == experience_id,
        )
    )
    bullet = result.scalar_one_or_none()

    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found")

    update_data = bullet_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bullet, field, value)

    await db.flush()
    await db.refresh(bullet)

    return bullet


@router.delete("/{experience_id}/bullets/{bullet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bullet(
    experience_id: UUID,
    bullet_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a bullet."""
    # Verify experience ownership
    exp_result = await db.execute(
        select(Experience).where(
            Experience.id == experience_id,
            Experience.user_id == current_user.id,
            Experience.deleted_at.is_(None),
        )
    )
    if not exp_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    result = await db.execute(
        select(ExperienceBullet).where(
            ExperienceBullet.id == bullet_id,
            ExperienceBullet.experience_id == experience_id,
        )
    )
    bullet = result.scalar_one_or_none()

    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found")

    await db.delete(bullet)
    await db.flush()


# Supporting documents
@router.post("/{experience_id}/supporting", response_model=SupportingDocResponse, status_code=status.HTTP_201_CREATED)
async def add_supporting_document(
    experience_id: UUID,
    doc_data: SupportingDocCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SupportingDocument:
    """Add a supporting document to an experience."""
    result = await db.execute(
        select(Experience).where(
            Experience.id == experience_id,
            Experience.user_id == current_user.id,
            Experience.deleted_at.is_(None),
        )
    )
    experience = result.scalar_one_or_none()

    if not experience:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    from src.models.database import SupportingDocType
    supporting_doc = SupportingDocument(
        user_id=current_user.id,
        experience_id=experience_id,
        doc_type=SupportingDocType(doc_data.doc_type),
        title=doc_data.title,
        description=doc_data.description,
        source_document_id=doc_data.source_document_id,
        authors=doc_data.authors,
        publication=doc_data.publication,
        doi_url=doc_data.doi_url,
        issuer=doc_data.issuer,
        issue_date=doc_data.issue_date,
        expiry_date=doc_data.expiry_date,
        credential_id=doc_data.credential_id,
        credential_url=doc_data.credential_url,
        recommender_name=doc_data.recommender_name,
        recommender_title=doc_data.recommender_title,
        relationship=doc_data.relationship,
        portfolio_url=doc_data.portfolio_url,
    )

    db.add(supporting_doc)
    await db.flush()
    await db.refresh(supporting_doc)

    return supporting_doc
