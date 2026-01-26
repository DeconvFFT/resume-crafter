"""Automation schemas for job search, applications, and networking."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


def convert_uuid(v: Any) -> str:
    """Convert UUID to string for JSON serialization."""
    if hasattr(v, "hex"):
        return str(v)
    return v


# ============ SearchCampaign Schemas ============


class SearchCampaignCreate(BaseModel):
    """Create a search campaign."""

    name: str = Field(..., min_length=1, max_length=255)
    target_roles: list[str] = Field(..., min_length=1)
    target_locations: list[str] = Field(default_factory=list)
    target_companies: list[str] | None = None
    keywords: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] | None = None
    min_salary: int | None = Field(None, ge=0)
    max_salary: int | None = Field(None, ge=0)
    remote_preference: str = Field("any", pattern="^(remote|hybrid|onsite|any)$")
    experience_level: str = Field("any", pattern="^(entry|mid|senior|lead|any)$")
    settings: dict[str, Any] | None = None


class SearchCampaignUpdate(BaseModel):
    """Update a search campaign. All fields optional for partial updates."""

    name: str | None = Field(None, min_length=1, max_length=255)
    status: str | None = Field(None, pattern="^(draft|active|paused|completed)$")
    target_roles: list[str] | None = None
    target_locations: list[str] | None = None
    target_companies: list[str] | None = None
    keywords: list[str] | None = None
    excluded_keywords: list[str] | None = None
    min_salary: int | None = Field(None, ge=0)
    max_salary: int | None = Field(None, ge=0)
    remote_preference: str | None = Field(None, pattern="^(remote|hybrid|onsite|any)$")
    experience_level: str | None = Field(None, pattern="^(entry|mid|senior|lead|any)$")
    settings: dict[str, Any] | None = None


class SearchCampaignResponse(BaseModel):
    """Search campaign response."""

    id: str
    user_id: str
    name: str
    status: str
    target_roles: list[str]
    target_locations: list[str]
    target_companies: list[str] | None
    keywords: list[str]
    excluded_keywords: list[str] | None
    min_salary: int | None
    max_salary: int | None
    remote_preference: str | None
    experience_level: str | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    settings: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)


class SearchCampaignListResponse(BaseModel):
    """List of search campaigns."""

    items: list[SearchCampaignResponse]
    total: int


# ============ DiscoveredJob Schemas ============
# Response only (jobs are discovered by agents, not created by users)


class DiscoveredJobResponse(BaseModel):
    """Discovered job response."""

    id: str
    campaign_id: str
    user_id: str
    external_id: str
    source: str
    title: str
    company: str
    location: str
    description: str
    requirements: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    url: str
    posted_at: datetime | None
    match_score: float | None
    match_reasoning: str | None
    is_qualified: bool | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "campaign_id", "user_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)


class DiscoveredJobListResponse(BaseModel):
    """List of discovered jobs."""

    items: list[DiscoveredJobResponse]
    total: int


# ============ JobApplication Schemas ============


class JobApplicationCreate(BaseModel):
    """Create a job application."""

    discovered_job_id: str | None = None
    campaign_id: str | None = None
    job_title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    job_url: str | None = Field(None, max_length=1024)
    notes: str | None = None


class JobApplicationUpdate(BaseModel):
    """Update a job application. All fields optional for partial updates."""

    status: str | None = Field(
        None,
        pattern="^(discovered|filtered|queued|resume_generated|applying|applied|viewed|response_received|interview_scheduled|rejected|offer_received)$",
    )
    resume_id: str | None = None
    cover_letter: str | None = None
    notes: str | None = None
    rejection_reason: str | None = Field(None, max_length=255)


class JobApplicationResponse(BaseModel):
    """Job application response."""

    id: str
    user_id: str
    discovered_job_id: str | None
    campaign_id: str | None
    status: str
    status_history: list[dict[str, Any]] | None
    job_title: str
    company: str
    job_url: str | None
    resume_id: str | None
    cover_letter: str | None
    applied_at: datetime | None
    response_received_at: datetime | None
    interview_scheduled_at: datetime | None
    notes: str | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)

    @field_validator("discovered_job_id", "campaign_id", "resume_id", mode="before")
    @classmethod
    def convert_optional_uuid_fields(cls, v: Any) -> str | None:
        """Convert optional UUID fields to string."""
        if v is None:
            return None
        return convert_uuid(v)


class JobApplicationListResponse(BaseModel):
    """List of job applications."""

    items: list[JobApplicationResponse]
    total: int


# ============ CompanyProfile Schemas ============


class CompanyProfileCreate(BaseModel):
    """Create a company profile."""

    name: str = Field(..., min_length=1, max_length=255)
    website: str | None = Field(None, max_length=512)
    linkedin_url: str | None = Field(None, max_length=512)
    careers_url: str | None = Field(None, max_length=512)
    industry: str | None = Field(None, max_length=255)
    size: str | None = Field(None, max_length=100)
    description: str | None = None
    tech_stack: list[str] | None = None
    culture_notes: str | None = None
    interview_process: str | None = None
    glassdoor_rating: float | None = Field(None, ge=0, le=5)


class CompanyProfileUpdate(BaseModel):
    """Update a company profile. All fields optional for partial updates."""

    name: str | None = Field(None, min_length=1, max_length=255)
    website: str | None = Field(None, max_length=512)
    linkedin_url: str | None = Field(None, max_length=512)
    careers_url: str | None = Field(None, max_length=512)
    industry: str | None = Field(None, max_length=255)
    size: str | None = Field(None, max_length=100)
    description: str | None = None
    tech_stack: list[str] | None = None
    culture_notes: str | None = None
    interview_process: str | None = None
    glassdoor_rating: float | None = Field(None, ge=0, le=5)
    research_data: dict[str, Any] | None = None


class CompanyProfileResponse(BaseModel):
    """Company profile response."""

    id: str
    user_id: str
    name: str
    website: str | None
    linkedin_url: str | None
    careers_url: str | None
    industry: str | None
    size: str | None
    description: str | None
    tech_stack: list[str] | None
    culture_notes: str | None
    interview_process: str | None
    glassdoor_rating: float | None
    research_data: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)


class CompanyProfileListResponse(BaseModel):
    """List of company profiles."""

    items: list[CompanyProfileResponse]
    total: int


# ============ CompanyContact Schemas ============


class CompanyContactCreate(BaseModel):
    """Create a company contact."""

    company_profile_id: str
    name: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    linkedin_url: str = Field(..., max_length=512)
    email: str | None = Field(None, max_length=255)
    relevance_score: float | None = Field(None, ge=0, le=100)
    notes: str | None = None


class CompanyContactUpdate(BaseModel):
    """Update a company contact. All fields optional for partial updates."""

    name: str | None = Field(None, min_length=1, max_length=255)
    title: str | None = Field(None, min_length=1, max_length=255)
    linkedin_url: str | None = Field(None, max_length=512)
    email: str | None = Field(None, max_length=255)
    relevance_score: float | None = Field(None, ge=0, le=100)
    notes: str | None = None


class CompanyContactResponse(BaseModel):
    """Company contact response."""

    id: str
    user_id: str
    company_profile_id: str
    name: str
    title: str
    linkedin_url: str
    email: str | None
    relevance_score: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", "company_profile_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)


class CompanyContactListResponse(BaseModel):
    """List of company contacts."""

    items: list[CompanyContactResponse]
    total: int


# ============ NetworkingOutreach Schemas ============


class NetworkingOutreachCreate(BaseModel):
    """Create a networking outreach message."""

    contact_id: str
    application_id: str | None = None
    channel: str = Field(..., pattern="^(linkedin|email)$")
    subject: str | None = Field(None, max_length=255)  # Required for email
    message: str = Field(..., min_length=10)


class NetworkingOutreachUpdate(BaseModel):
    """Update a networking outreach. All fields optional for partial updates."""

    status: str | None = Field(
        None, pattern="^(pending|draft_ready|sent|connected|no_response)$"
    )
    subject: str | None = Field(None, max_length=255)
    message: str | None = Field(None, min_length=10)


class NetworkingOutreachResponse(BaseModel):
    """Networking outreach response."""

    id: str
    user_id: str
    contact_id: str
    application_id: str | None
    channel: str
    status: str
    subject: str | None
    message: str
    sent_at: datetime | None
    response_received_at: datetime | None
    follow_up_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", "contact_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)

    @field_validator("application_id", mode="before")
    @classmethod
    def convert_optional_uuid_fields(cls, v: Any) -> str | None:
        """Convert optional UUID fields to string."""
        if v is None:
            return None
        return convert_uuid(v)


class NetworkingOutreachListResponse(BaseModel):
    """List of networking outreach messages."""

    items: list[NetworkingOutreachResponse]
    total: int


# ============ AutomationLog Schemas ============
# Response only (logs are created by the system)


class AutomationLogResponse(BaseModel):
    """Automation log response."""

    id: str
    user_id: str
    action_type: str
    entity_type: str
    entity_id: str | None
    status: str
    details: dict[str, Any] | None
    duration_ms: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)

    @field_validator("entity_id", mode="before")
    @classmethod
    def convert_optional_uuid_fields(cls, v: Any) -> str | None:
        """Convert optional UUID fields to string."""
        if v is None:
            return None
        return convert_uuid(v)


class AutomationLogListResponse(BaseModel):
    """List of automation logs."""

    items: list[AutomationLogResponse]
    total: int


# ============ Paginated Response ============

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


# ============ Statistics/Summary Schemas ============


class CampaignStats(BaseModel):
    """Statistics for a search campaign."""

    campaign_id: str
    total_jobs_discovered: int
    qualified_jobs: int
    applications_submitted: int
    responses_received: int
    interviews_scheduled: int
    offers_received: int


class ApplicationPipelineStats(BaseModel):
    """Application pipeline statistics."""

    discovered: int = 0
    filtered: int = 0
    queued: int = 0
    resume_generated: int = 0
    applying: int = 0
    applied: int = 0
    viewed: int = 0
    response_received: int = 0
    interview_scheduled: int = 0
    rejected: int = 0
    offer_received: int = 0


class AutomationDashboard(BaseModel):
    """Dashboard summary for automation features."""

    active_campaigns: int
    total_jobs_discovered: int
    pending_applications: int
    applications_this_week: int
    response_rate: float
    interview_rate: float
    pipeline_stats: ApplicationPipelineStats
