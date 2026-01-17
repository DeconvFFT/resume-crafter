"""Pydantic schemas for publications."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class PublicationCreate(BaseModel):
    """Schema for creating a publication."""

    title: str = Field(..., min_length=1, max_length=512)
    authors: str = Field(..., min_length=1, description="Comma-separated list of authors")
    publication_type: Literal[
        "journal",
        "conference",
        "workshop",
        "preprint",
        "thesis",
        "book_chapter",
        "patent",
        "other",
    ] = "other"
    venue: str | None = Field(None, max_length=255)
    publisher: str | None = Field(None, max_length=255)
    publication_date: date | None = None
    doi: str | None = Field(None, max_length=255)
    arxiv_id: str | None = Field(None, max_length=100)
    url: str | None = Field(None, max_length=1024)
    abstract: str | None = None
    citation_count: int | None = Field(None, ge=0)
    is_first_author: bool = False
    author_position: int | None = Field(None, ge=1)
    display_order: int = 0


class PublicationUpdate(BaseModel):
    """Schema for updating a publication."""

    title: str | None = Field(None, min_length=1, max_length=512)
    authors: str | None = None
    publication_type: Literal[
        "journal",
        "conference",
        "workshop",
        "preprint",
        "thesis",
        "book_chapter",
        "patent",
        "other",
    ] | None = None
    venue: str | None = None
    publisher: str | None = None
    publication_date: date | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    abstract: str | None = None
    citation_count: int | None = None
    is_first_author: bool | None = None
    author_position: int | None = None
    display_order: int | None = None


class PublicationResponse(BaseModel):
    """Schema for publication response."""

    id: UUID
    user_id: UUID
    source_document_id: UUID | None
    title: str
    authors: str
    publication_type: str
    venue: str | None
    publisher: str | None
    publication_date: date | None
    doi: str | None
    arxiv_id: str | None
    url: str | None
    abstract: str | None
    citation_count: int | None
    is_first_author: bool
    author_position: int | None
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PublicationListResponse(BaseModel):
    """Schema for publication list response."""

    items: list[PublicationResponse]
    total: int


class PublicationTypeGroup(BaseModel):
    """Schema for publications grouped by type."""

    publication_type: str
    publications: list[PublicationResponse]
