"""Resume matching and generation schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def convert_uuid(v: Any) -> str:
    """Convert UUID to string for JSON serialization."""
    if hasattr(v, 'hex'):
        return str(v)
    return v


class MatchRequest(BaseModel):
    """Request to generate resume matches for a job."""

    job_id: UUID
    max_experience_bullets: int = Field(10, ge=1, le=20)
    max_project_bullets: int = Field(6, ge=1, le=15)


class MatchItemResponse(BaseModel):
    """Individual match item response."""

    id: str
    requirement_id: str
    requirement_content: str
    experience_bullet_id: str | None
    project_bullet_id: str | None
    bullet_content: str
    bullet_source: Literal["experience", "project"]
    relevance_score: float = Field(ge=0.0, le=1.0)
    match_explanation: str | None
    included_in_resume: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "requirement_id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)

    @field_validator("experience_bullet_id", "project_bullet_id", mode="before")
    @classmethod
    def convert_optional_uuid(cls, v):
        """Convert optional UUID to string."""
        if v is None:
            return None
        return convert_uuid(v)


class MatchResponse(BaseModel):
    """Resume match response."""

    id: str
    job_id: str
    job_role: str | None
    job_company: str | None
    overall_match_score: float = Field(ge=0.0, le=1.0)
    skill_coverage: float = Field(ge=0.0, le=1.0)
    experience_relevance: float = Field(ge=0.0, le=1.0)
    processing_status: str
    items: list[MatchItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "job_id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)


class MatchListResponse(BaseModel):
    """List of resume matches."""

    items: list[MatchResponse]
    total: int


class ToggleMatchItemRequest(BaseModel):
    """Request to toggle a match item's inclusion in resume."""

    included: bool


class ResumeGenerateRequest(BaseModel):
    """Request to generate final resume."""

    match_id: UUID
    format: Literal["json", "markdown", "google_doc"] = "json"


class ResumeSection(BaseModel):
    """Section of generated resume."""

    title: str
    items: list[str]


class GeneratedResume(BaseModel):
    """Generated resume content."""

    profile: dict
    experiences: list[dict]
    projects: list[dict]
    skills: list[str]
    publications: list[dict] = []


class ResumeGenerateResponse(BaseModel):
    """Resume generation response."""

    match_id: str
    format: str
    content: GeneratedResume | str  # JSON object or markdown/gdoc URL
    google_doc_url: str | None = None

    @field_validator("match_id", mode="before")
    @classmethod
    def convert_match_id_uuid(cls, v):
        """Convert UUID to string."""
        return convert_uuid(v)
