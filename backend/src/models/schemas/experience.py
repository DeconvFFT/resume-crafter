"""Experience schemas."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def convert_uuid(v: Any) -> str:
    """Convert UUID to string for JSON serialization."""
    if hasattr(v, 'hex'):
        return str(v)
    return v


class BulletCreate(BaseModel):
    """Create a bullet point."""

    content: str = Field(..., min_length=10, max_length=1000)
    order_index: int = Field(0, ge=0)


class BulletUpdate(BaseModel):
    """Update a bullet point."""

    content: str | None = Field(None, min_length=10, max_length=1000)
    order_index: int | None = Field(None, ge=0)


class BulletResponse(BaseModel):
    """Bullet point response."""

    id: str
    content: str
    order_index: int
    skills: list[str] | None
    metrics: str | None
    action_verbs: list[str] | None
    embedding_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)


class ExperienceCreate(BaseModel):
    """Create an experience entry."""

    company: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    location: str | None = Field(None, max_length=255)
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    bullets: list[BulletCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "ExperienceCreate":
        """Validate end_date is after start_date."""
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        if self.is_current and self.end_date:
            raise ValueError("Current position cannot have an end_date")
        return self


class ExperienceUpdate(BaseModel):
    """Update an experience entry."""

    company: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, min_length=1, max_length=255)
    location: str | None = Field(None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None


class ExperienceResponse(BaseModel):
    """Experience entry response."""

    id: str
    company: str
    role: str
    location: str | None
    start_date: date
    end_date: date | None
    is_current: bool
    bullets: list[BulletResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)


class ExperienceListResponse(BaseModel):
    """List of experiences."""

    items: list[ExperienceResponse]
    total: int
