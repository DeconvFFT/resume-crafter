"""Execution tracking schemas for workflow monitoring."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def convert_uuid(v: Any) -> str:
    """Convert UUID to string for JSON serialization."""
    if hasattr(v, "hex"):
        return str(v)
    return v


class ExecutionStatus(str, Enum):
    """Status of a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStepStatus(str, Enum):
    """Status of an individual execution step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowType(str, Enum):
    """Types of automated workflows."""

    JOB_DISCOVERY = "job_discovery"
    JOB_ANALYSIS = "job_analysis"
    RESUME_GENERATION = "resume_generation"
    APPLICATION_PROCESSING = "application_processing"
    COMPANY_RESEARCH = "company_research"
    CONTACT_DISCOVERY = "contact_discovery"
    OUTREACH_GENERATION = "outreach_generation"


# ============ Execution Step Schemas ============


class ExecutionStepCreate(BaseModel):
    """Create an execution step."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    order_index: int = Field(default=0, ge=0)
    metadata: dict[str, Any] | None = None


class ExecutionStepResponse(BaseModel):
    """Execution step response."""

    id: str
    execution_id: str
    name: str
    description: str | None
    status: ExecutionStepStatus
    order_index: int
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    result: dict[str, Any] | None
    error_message: str | None
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "execution_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)


# ============ Execution Log Schemas ============


class LogLevel(str, Enum):
    """Log level for execution logs."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ExecutionLogEntry(BaseModel):
    """Single log entry for an execution."""

    id: str
    execution_id: str
    step_id: str | None
    level: LogLevel
    message: str
    data: dict[str, Any] | None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "execution_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)

    @field_validator("step_id", mode="before")
    @classmethod
    def convert_optional_uuid(cls, v: Any) -> str | None:
        """Convert optional UUID fields to string."""
        if v is None:
            return None
        return convert_uuid(v)


class ExecutionLogListResponse(BaseModel):
    """List of execution logs."""

    items: list[ExecutionLogEntry]
    total: int
    has_more: bool


# ============ Execution Schemas ============


class ExecutionCreate(BaseModel):
    """Create a workflow execution."""

    workflow_type: WorkflowType
    campaign_id: str | None = None
    entity_id: str | None = None
    entity_type: str | None = None
    config: dict[str, Any] | None = None
    scheduled_at: datetime | None = None


class ExecutionResponse(BaseModel):
    """Workflow execution response."""

    id: str
    user_id: str
    workflow_type: WorkflowType
    status: ExecutionStatus
    campaign_id: str | None
    entity_id: str | None
    entity_type: str | None
    config: dict[str, Any] | None
    progress: int  # 0-100
    current_step: str | None
    total_steps: int
    completed_steps: int
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    result: dict[str, Any] | None
    error_message: str | None
    scheduled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)

    @field_validator("campaign_id", "entity_id", mode="before")
    @classmethod
    def convert_optional_uuid_fields(cls, v: Any) -> str | None:
        """Convert optional UUID fields to string."""
        if v is None:
            return None
        return convert_uuid(v)


class ExecutionDetailResponse(ExecutionResponse):
    """Detailed execution response with steps."""

    steps: list[ExecutionStepResponse] = Field(default_factory=list)
    recent_logs: list[ExecutionLogEntry] = Field(default_factory=list)


class ExecutionListResponse(BaseModel):
    """List of executions."""

    items: list[ExecutionResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============ Execution Filter Schemas ============


class ExecutionFilter(BaseModel):
    """Filter parameters for listing executions."""

    workflow_type: WorkflowType | None = None
    status: ExecutionStatus | None = None
    campaign_id: str | None = None
    entity_id: str | None = None
    started_after: datetime | None = None
    started_before: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ============ Execution Action Schemas ============


class ExecutionCancelRequest(BaseModel):
    """Request to cancel an execution."""

    reason: str | None = Field(None, max_length=500)


class ExecutionCancelResponse(BaseModel):
    """Response after cancelling an execution."""

    id: str
    status: ExecutionStatus
    cancelled_at: datetime
    reason: str | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_fields(cls, v: Any) -> str:
        """Convert UUID fields to string."""
        return convert_uuid(v)


# ============ SSE Event Schemas ============


class ExecutionSSEEvent(BaseModel):
    """Server-Sent Event for execution updates."""

    event_type: str  # log, step_update, status_change, progress, done, error
    execution_id: str
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)

    def to_sse_data(self) -> str:
        """Format as SSE data payload."""
        import json
        return json.dumps(self.model_dump())


# ============ Cron Job Schemas ============


class CronJobStatus(str, Enum):
    """Status of a cron job."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class CronJobType(str, Enum):
    """Types of cron jobs."""

    JOB_DISCOVERY = "job_discovery"
    JOB_ANALYSIS = "job_analysis"
    APPLICATION_QUEUE = "application_queue"


class CronJobConfig(BaseModel):
    """Configuration for a cron job."""

    job_type: CronJobType
    interval_seconds: int = Field(..., ge=60)  # Minimum 1 minute
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=0)
    config: dict[str, Any] | None = None


class CronJobResponse(BaseModel):
    """Response for cron job status."""

    job_type: CronJobType
    status: CronJobStatus
    interval_seconds: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    last_run_status: str | None  # success, failed
    last_run_duration_ms: int | None
    run_count: int
    error_count: int
    config: dict[str, Any] | None


class CronJobListResponse(BaseModel):
    """List of cron jobs."""

    items: list[CronJobResponse]


class CronJobSchedule(BaseModel):
    """Cron job schedule configuration."""

    job_discovery_interval_hours: int = Field(default=4, ge=1, le=24)
    job_analysis_interval_hours: int = Field(default=1, ge=1, le=24)
    application_queue_delay_seconds: int = Field(default=30, ge=10, le=300)
    application_queue_batch_size: int = Field(default=5, ge=1, le=20)
