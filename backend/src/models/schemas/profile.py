"""Profile schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class ProfileUpdate(BaseModel):
    """Profile update request."""

    full_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=255)
    websites: list[str] | None = Field(None, max_length=10)
    linkedin_url: str | None = Field(None, max_length=512)
    summary: str | None = Field(None, max_length=2000)


class ProfileResponse(BaseModel):
    """Profile response."""

    id: UUID
    email: EmailStr
    full_name: str | None
    phone: str | None
    location: str | None
    websites: list[str] | None
    linkedin_url: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
