"""Job description schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobAnalysisRequest(BaseModel):
    """Request to analyze a job description."""

    source_url: str | None = Field(None, max_length=1024, description="URL to fetch job description from")
    raw_text: str | None = Field(None, max_length=50000, description="Raw job description text")

    def model_post_init(self, __context: object) -> None:
        """Validate at least one source is provided."""
        if not self.source_url and not self.raw_text:
            raise ValueError("Either source_url or raw_text must be provided")


class RequirementResponse(BaseModel):
    """Job requirement response."""

    id: str
    content: str
    requirement_type: str
    importance_score: int = Field(ge=1, le=5)
    keywords: list[str] | None = None
    embedding_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string."""
        if hasattr(v, 'hex'):
            return str(v)
        return v


class JobResponse(BaseModel):
    """Job description response."""

    id: str
    source_url: str | None = None
    company: str | None = None
    role: str | None = None
    location: str | None = None
    salary_range: str | None = None
    experience_level: str | None = None
    processing_status: str
    processing_error: str | None = None
    requirements: list[RequirementResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string."""
        if hasattr(v, 'hex'):
            return str(v)
        return v


class JobListResponse(BaseModel):
    """List of job descriptions."""

    items: list[JobResponse]
    total: int


class ExtractedRequirement(BaseModel):
    """LLM-extracted requirement from job description."""

    content: str = Field(..., description="The requirement text")
    requirement_type: Literal["skill", "experience", "education", "certification", "soft_skill", "other"]
    importance: int = Field(ge=1, le=5, description="Importance score 1-5")
    keywords: list[str] = Field(default_factory=list, description="Key terms in this requirement")


class JobExtractionResult(BaseModel):
    """LLM extraction result for job description."""

    company: str | None
    role: str | None
    location: str | None
    salary_range: str | None
    experience_level: Literal["entry", "junior", "mid", "senior", "lead", "principal"] | None
    requirements: list[ExtractedRequirement]
