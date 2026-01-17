"""Pydantic schemas for skills."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    """Schema for creating a skill."""

    name: str = Field(..., min_length=1, max_length=100)
    category: Literal[
        "programming_language",
        "framework",
        "database",
        "cloud",
        "devops",
        "tool",
        "soft_skill",
        "methodology",
        "other",
    ] = "other"
    proficiency: Literal["beginner", "intermediate", "advanced", "expert"] | None = None
    years_of_experience: int | None = Field(None, ge=0, le=50)
    is_highlighted: bool = False
    display_order: int = 0


class SkillUpdate(BaseModel):
    """Schema for updating a skill."""

    name: str | None = Field(None, min_length=1, max_length=100)
    category: Literal[
        "programming_language",
        "framework",
        "database",
        "cloud",
        "devops",
        "tool",
        "soft_skill",
        "methodology",
        "other",
    ] | None = None
    proficiency: Literal["beginner", "intermediate", "advanced", "expert"] | None = None
    years_of_experience: int | None = Field(None, ge=0, le=50)
    is_highlighted: bool | None = None
    display_order: int | None = None


class SkillResponse(BaseModel):
    """Schema for skill response."""

    id: UUID
    user_id: UUID
    name: str
    category: str
    proficiency: str | None
    years_of_experience: int | None
    is_highlighted: bool
    display_order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SkillListResponse(BaseModel):
    """Schema for skill list response."""

    items: list[SkillResponse]
    total: int


class BulkSkillCreate(BaseModel):
    """Schema for creating multiple skills at once."""

    skills: list[SkillCreate]


class SkillCategoryGroup(BaseModel):
    """Schema for skills grouped by category."""

    category: str
    skills: list[SkillResponse]
