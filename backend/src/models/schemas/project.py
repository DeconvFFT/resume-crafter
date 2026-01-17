"""Project schemas."""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def convert_uuid(v: Any) -> str:
    """Convert UUID to string for JSON serialization."""
    if hasattr(v, 'hex'):
        return str(v)
    return v


class ProjectBulletCreate(BaseModel):
    """Create a project bullet point."""

    content: str = Field(..., min_length=10, max_length=1000)
    order_index: int = Field(0, ge=0)


class ProjectBulletUpdate(BaseModel):
    """Update a project bullet point."""

    content: str | None = Field(None, min_length=10, max_length=1000)
    order_index: int | None = Field(None, ge=0)


class ProjectBulletResponse(BaseModel):
    """Project bullet point response."""

    id: str
    content: str
    order_index: int
    skills: list[str] | None
    metrics: str | None
    embedding_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)


class LinkCreate(BaseModel):
    """Create a project link."""

    url: str = Field(..., max_length=1024)
    link_type: Literal["github", "demo", "paper", "docs", "video", "other"]
    title: str | None = Field(None, max_length=255)


class LinkUpdate(BaseModel):
    """Update a project link."""

    url: str | None = Field(None, max_length=1024)
    link_type: Literal["github", "demo", "paper", "docs", "video", "other"] | None = None
    title: str | None = Field(None, max_length=255)


class LinkResponse(BaseModel):
    """Project link response."""

    id: str
    url: str
    link_type: str
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)


class ProjectCreate(BaseModel):
    """Create a project entry."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    technologies: list[str] | None = Field(None, max_length=20)
    start_date: date | None = None
    end_date: date | None = None
    bullets: list[ProjectBulletCreate] = Field(default_factory=list)
    links: list[LinkCreate] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    """Update a project entry."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    technologies: list[str] | None = Field(None, max_length=20)
    start_date: date | None = None
    end_date: date | None = None


class ProjectResponse(BaseModel):
    """Project entry response."""

    id: str
    name: str
    description: str | None
    technologies: list[str] | None
    start_date: date | None
    end_date: date | None
    bullets: list[ProjectBulletResponse]
    links: list[LinkResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)


class ProjectListResponse(BaseModel):
    """List of projects."""

    items: list[ProjectResponse]
    total: int


class SupportingDocCreate(BaseModel):
    """Create a supporting document."""

    doc_type: Literal["paper", "certification", "recommendation", "portfolio", "other"]
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    source_document_id: UUID | None = None

    # Paper fields
    authors: str | None = None
    publication: str | None = None
    doi_url: str | None = None

    # Certification fields
    issuer: str | None = None
    issue_date: date | None = None
    expiry_date: date | None = None
    credential_id: str | None = None
    credential_url: str | None = None

    # Recommendation fields
    recommender_name: str | None = None
    recommender_title: str | None = None
    relationship: str | None = None

    # Portfolio fields
    portfolio_url: str | None = None


class SupportingDocResponse(BaseModel):
    """Supporting document response."""

    id: str
    doc_type: str
    title: str
    description: str | None
    authors: str | None
    publication: str | None
    doi_url: str | None
    issuer: str | None
    issue_date: date | None
    expiry_date: date | None
    credential_id: str | None
    credential_url: str | None
    recommender_name: str | None
    recommender_title: str | None
    relationship: str | None
    portfolio_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)
