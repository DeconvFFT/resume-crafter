"""Publications routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.models.database import Publication, PublicationType
from src.models.schemas.publication import (
    PublicationCreate,
    PublicationListResponse,
    PublicationResponse,
    PublicationUpdate,
    PublicationTypeGroup,
)
from src.storage.database import get_db

router = APIRouter()


@router.post("", response_model=PublicationResponse, status_code=status.HTTP_201_CREATED)
async def create_publication(
    pub_data: PublicationCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Publication:
    """Create a new publication."""
    publication = Publication(
        user_id=current_user.id,
        title=pub_data.title,
        authors=pub_data.authors,
        publication_type=PublicationType(pub_data.publication_type),
        venue=pub_data.venue,
        publisher=pub_data.publisher,
        publication_date=pub_data.publication_date,
        doi=pub_data.doi,
        arxiv_id=pub_data.arxiv_id,
        url=pub_data.url,
        abstract=pub_data.abstract,
        citation_count=pub_data.citation_count,
        is_first_author=pub_data.is_first_author,
        author_position=pub_data.author_position,
        display_order=pub_data.display_order,
    )
    db.add(publication)
    await db.flush()
    await db.refresh(publication)
    return publication


@router.get("", response_model=PublicationListResponse)
async def list_publications(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    publication_type: str | None = None,
) -> PublicationListResponse:
    """List all publications for current user, optionally filtered by type."""
    query = select(Publication).where(
        Publication.user_id == current_user.id,
        Publication.deleted_at.is_(None),
    )

    if publication_type:
        query = query.where(Publication.publication_type == PublicationType(publication_type))

    query = query.order_by(Publication.display_order, Publication.publication_date.desc())
    result = await db.execute(query)
    publications = result.scalars().all()

    return PublicationListResponse(items=list(publications), total=len(publications))


@router.get("/grouped", response_model=list[PublicationTypeGroup])
async def list_publications_grouped(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PublicationTypeGroup]:
    """List publications grouped by type."""
    result = await db.execute(
        select(Publication)
        .where(Publication.user_id == current_user.id, Publication.deleted_at.is_(None))
        .order_by(Publication.publication_type, Publication.display_order, Publication.publication_date.desc())
    )
    publications = result.scalars().all()

    # Group by type
    groups: dict[str, list[Publication]] = {}
    for pub in publications:
        pub_type = pub.publication_type.value
        if pub_type not in groups:
            groups[pub_type] = []
        groups[pub_type].append(pub)

    return [
        PublicationTypeGroup(publication_type=pub_type, publications=pubs)
        for pub_type, pubs in groups.items()
    ]


@router.get("/{publication_id}", response_model=PublicationResponse)
async def get_publication(
    publication_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Publication:
    """Get a specific publication."""
    result = await db.execute(
        select(Publication).where(
            Publication.id == publication_id,
            Publication.user_id == current_user.id,
            Publication.deleted_at.is_(None),
        )
    )
    publication = result.scalar_one_or_none()

    if not publication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")

    return publication


@router.patch("/{publication_id}", response_model=PublicationResponse)
async def update_publication(
    publication_id: UUID,
    pub_data: PublicationUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Publication:
    """Update a publication."""
    result = await db.execute(
        select(Publication).where(
            Publication.id == publication_id,
            Publication.user_id == current_user.id,
            Publication.deleted_at.is_(None),
        )
    )
    publication = result.scalar_one_or_none()

    if not publication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")

    update_data = pub_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "publication_type" and value:
            value = PublicationType(value)
        setattr(publication, field, value)

    await db.flush()
    await db.refresh(publication)

    return publication


@router.delete("/{publication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_publication(
    publication_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft delete a publication."""
    result = await db.execute(
        select(Publication).where(
            Publication.id == publication_id,
            Publication.user_id == current_user.id,
            Publication.deleted_at.is_(None),
        )
    )
    publication = result.scalar_one_or_none()

    if not publication:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication not found")

    from datetime import datetime, timezone
    publication.deleted_at = datetime.now(timezone.utc)

    await db.flush()
