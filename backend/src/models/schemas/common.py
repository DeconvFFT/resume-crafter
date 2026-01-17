"""Common schemas used across the API."""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


def convert_uuid(v: Any) -> str:
    """Convert UUID to string for JSON serialization."""
    if hasattr(v, 'hex'):
        return str(v)
    return v


class BaseResponseModel(BaseModel):
    """Base model for API responses with common UUID handling."""

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before", check_fields=False)
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)


class ErrorResponse(BaseModel):
    """Standardized error response for all API errors."""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    detail: str | None = Field(None, description="Additional error details")
    correlation_id: str = Field(..., description="Request correlation ID for debugging")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "detail": "Email format is invalid",
                "correlation_id": "abc123-def456",
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    items: list[T]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class TaskStatusResponse(BaseModel):
    """Response for background task status polling."""

    id: str = Field(alias="id")
    task_type: str
    status: str  # pending, processing, completed, failed
    progress: int = Field(ge=0, le=100)
    result: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_id(cls, v):
        """Convert UUID to string."""
        return convert_uuid(v)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status: healthy, degraded, unhealthy")
    version: str
    database: str = Field(..., description="Database connection status")
    redis: str = Field(..., description="Redis connection status")
    chromadb: str = Field(..., description="ChromaDB connection status")
