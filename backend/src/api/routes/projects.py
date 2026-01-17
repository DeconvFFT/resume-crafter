"""Project routes."""

import logging
from typing import Annotated
from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import CurrentUser
from src.models.database import BackgroundTask, Project, ProjectBullet, ProjectLink, SupportingDocument, TaskStatus
from src.models.schemas.project import (
    LinkCreate,
    LinkResponse,
    LinkUpdate,
    ProjectBulletCreate,
    ProjectBulletResponse,
    ProjectBulletUpdate,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    SupportingDocCreate,
    SupportingDocResponse,
)
from src.storage.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_arq_redis() -> ArqRedis:
    """Get ARQ Redis connection."""
    from arq import create_pool
    from src.tasks.worker import get_redis_settings
    return await create_pool(get_redis_settings())


async def _trigger_github_enrichment(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
    github_url: str,
) -> None:
    """Auto-trigger GitHub enrichment for a project.

    This is called automatically when a GitHub link is detected during
    project creation or when a GitHub link is added to an existing project.
    """
    from src.integrations.github import GitHubService

    # Validate GitHub URL
    parsed = GitHubService.parse_github_url(github_url)
    if not parsed:
        logger.warning(f"Invalid GitHub URL, skipping auto-enrichment: {github_url}")
        return

    # Create background task record
    task = BackgroundTask(
        user_id=user_id,
        task_type="enrich_project",
        entity_id=project_id,
        status=TaskStatus.PENDING,
        progress=0,
    )
    db.add(task)
    await db.flush()

    # Enqueue enrichment task
    try:
        arq = await get_arq_redis()
        await arq.enqueue_job(
            "enrich_project_from_github",
            project_id,
            user_id,
            github_url,
        )
        await arq.close()
        logger.info(f"Auto-triggered enrichment for project {project_id} from {github_url}")
    except Exception as e:
        logger.warning(f"Failed to auto-enqueue project enrichment: {e}")
        # Update task status to failed but don't raise - this is a background enhancement
        task.status = TaskStatus.FAILED
        task.error_message = str(e)


class ProjectEnrichRequest(BaseModel):
    """Request to enrich a project from GitHub."""

    github_url: str


class ProjectEnrichResponse(BaseModel):
    """Response for project enrichment request."""

    task_id: UUID
    message: str


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Project:
    """Create a new project entry."""
    project = Project(
        user_id=current_user.id,
        name=project_data.name,
        description=project_data.description,
        technologies=project_data.technologies,
        start_date=project_data.start_date,
        end_date=project_data.end_date,
    )

    # Add bullets
    for idx, bullet_data in enumerate(project_data.bullets):
        bullet = ProjectBullet(
            content=bullet_data.content,
            order_index=bullet_data.order_index or idx,
        )
        project.bullets.append(bullet)

    # Add links
    for link_data in project_data.links:
        from src.models.database import LinkType
        link = ProjectLink(
            url=link_data.url,
            link_type=LinkType(link_data.link_type),
            title=link_data.title,
        )
        project.links.append(link)

    db.add(project)
    await db.flush()
    await db.refresh(project, ["bullets", "links"])

    # Auto-trigger enrichment if a GitHub link was provided
    from src.models.database import LinkType
    github_link = next(
        (link for link in project.links if link.link_type == LinkType.GITHUB),
        None
    )
    if github_link:
        await _trigger_github_enrichment(db, project.id, current_user.id, github_link.url)

    return project


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectListResponse:
    """List all projects for current user."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.bullets), selectinload(Project.links))
        .where(Project.user_id == current_user.id, Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    return ProjectListResponse(items=list(projects), total=len(projects))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Project:
    """Get a specific project."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.bullets), selectinload(Project.links))
        .where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Project:
    """Update a project entry."""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.bullets), selectinload(Project.links))
        .where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    update_data = project_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project, ["bullets", "links"])

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft delete a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    from datetime import datetime, timezone
    project.deleted_at = datetime.now(timezone.utc)

    await db.flush()


# Bullet endpoints
@router.post("/{project_id}/bullets", response_model=ProjectBulletResponse, status_code=status.HTTP_201_CREATED)
async def add_project_bullet(
    project_id: UUID,
    bullet_data: ProjectBulletCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectBullet:
    """Add a bullet to a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    bullet = ProjectBullet(
        project_id=project_id,
        content=bullet_data.content,
        order_index=bullet_data.order_index,
    )

    db.add(bullet)
    await db.flush()
    await db.refresh(bullet)

    return bullet


@router.delete("/{project_id}/bullets/{bullet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_bullet(
    project_id: UUID,
    bullet_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a project bullet."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(ProjectBullet).where(
            ProjectBullet.id == bullet_id,
            ProjectBullet.project_id == project_id,
        )
    )
    bullet = result.scalar_one_or_none()

    if not bullet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bullet not found")

    await db.delete(bullet)
    await db.flush()


# Link endpoints
@router.post("/{project_id}/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def add_project_link(
    project_id: UUID,
    link_data: LinkCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectLink:
    """Add a link to a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    from src.models.database import LinkType
    link = ProjectLink(
        project_id=project_id,
        url=link_data.url,
        link_type=LinkType(link_data.link_type),
        title=link_data.title,
    )

    db.add(link)
    await db.flush()
    await db.refresh(link)

    # Auto-trigger enrichment if this is a GitHub link
    if link.link_type == LinkType.GITHUB:
        await _trigger_github_enrichment(db, project_id, current_user.id, link.url)

    return link


@router.delete("/{project_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_link(
    project_id: UUID,
    link_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a project link."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(
        select(ProjectLink).where(
            ProjectLink.id == link_id,
            ProjectLink.project_id == project_id,
        )
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    await db.delete(link)
    await db.flush()


# GitHub enrichment
@router.post("/{project_id}/enrich", response_model=ProjectEnrichResponse, status_code=status.HTTP_202_ACCEPTED)
async def enrich_project_from_github(
    project_id: UUID,
    request: ProjectEnrichRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectEnrichResponse:
    """Enrich a project with data from GitHub.

    This triggers a multi-agent pipeline that:
    1. Fetches repository data from GitHub API
    2. Analyzes and understands the project
    3. Generates resume-ready bullet points
    """
    # Verify project ownership
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate GitHub URL
    from src.integrations.github import GitHubService

    parsed = GitHubService.parse_github_url(request.github_url)
    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub URL. Expected format: https://github.com/owner/repo",
        )

    # Create background task record
    task = BackgroundTask(
        user_id=current_user.id,
        task_type="enrich_project",
        entity_id=project_id,
        status=TaskStatus.PENDING,
        progress=0,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Enqueue enrichment task
    try:
        arq = await get_arq_redis()
        await arq.enqueue_job(
            "enrich_project_from_github",
            project_id,
            current_user.id,
            request.github_url,
        )
        await arq.close()
        logger.info(f"Enqueued project enrichment for {project_id} from {request.github_url}")
    except Exception as e:
        logger.warning(f"Failed to enqueue project enrichment: {e}")
        # Update task status to failed
        task.status = TaskStatus.FAILED
        task.error_message = str(e)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to queue enrichment task. Please try again.",
        )

    return ProjectEnrichResponse(
        task_id=task.id,
        message="Project enrichment started. Bullets will be added when complete.",
    )


# Supporting documents
@router.post("/{project_id}/supporting", response_model=SupportingDocResponse, status_code=status.HTTP_201_CREATED)
async def add_project_supporting_document(
    project_id: UUID,
    doc_data: SupportingDocCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SupportingDocument:
    """Add a supporting document to a project."""
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.deleted_at.is_(None),
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    from src.models.database import SupportingDocType
    supporting_doc = SupportingDocument(
        user_id=current_user.id,
        project_id=project_id,
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
