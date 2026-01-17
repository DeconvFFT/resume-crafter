"""Document schemas."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def convert_uuid(v: Any) -> str:
    """Convert UUID to string for JSON serialization."""
    if hasattr(v, 'hex'):
        return str(v)
    return v


class DocumentUpload(BaseModel):
    """Document upload request metadata."""

    filename: str = Field(..., max_length=255)
    source_type: Literal["local_file", "google_doc", "url"] = "local_file"
    source_url: str | None = Field(None, max_length=1024)
    hint_document_class: Literal["experience", "project", "supporting"] | None = None


class DocumentClassificationResult(BaseModel):
    """Classification result from LLM."""

    document_class: Literal["experience", "project", "supporting"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class DocumentVerifyRequest(BaseModel):
    """Request to verify/correct document classification."""

    document_class: Literal["resume", "experience", "project", "supporting"]


class ProcessingLogEntry(BaseModel):
    """A single log entry for document processing."""

    timestamp: str
    step: str
    status: str
    message: str
    details: dict | None = None


class DocumentResponse(BaseModel):
    """Document response."""

    id: str
    filename: str
    mime_type: str | None
    source_type: str
    source_url: str | None
    document_class: str | None
    classification_confidence: float | None
    classification_reasoning: str | None
    verified_by_user: bool
    processing_status: str
    processing_error: str | None
    processing_logs: list[ProcessingLogEntry] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_id_uuid(cls, v):
        """Convert UUID id to string."""
        return convert_uuid(v)


class DocumentListResponse(BaseModel):
    """List of documents."""

    items: list[DocumentResponse]
    total: int


class GoogleDocImportRequest(BaseModel):
    """Request to import a Google Doc."""

    google_doc_id: str = Field(..., description="Google Doc ID from URL")
    hint_document_class: Literal["experience", "project", "supporting"] | None = None
