"""Gmail MCP integration for email draft creation.

This module provides integration with Gmail via the @anthropic/gmail-mcp package
for creating email drafts with HTML formatting and attachments. Drafts are created
but NOT sent - users must manually review and send them.

Usage:
    from src.integrations.gmail_mcp import GmailMCPService, EmailDraft

    service = GmailMCPService(config)
    draft = EmailDraft(
        to=["recipient@example.com"],
        subject="Job Application: Software Engineer",
        body_html="<p>Dear Hiring Manager...</p>",
        attachments=[Attachment(filename="resume.pdf", content=pdf_bytes, mime_type="application/pdf")]
    )
    result = await service.create_draft(draft)
"""

import base64
import json
import logging
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from string import Template
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Models
# =============================================================================


class GmailAuthType(str, Enum):
    """Authentication type for Gmail API."""

    OAUTH2 = "oauth2"
    SERVICE_ACCOUNT = "service_account"


class GmailConfig(BaseModel):
    """Configuration for Gmail OAuth credentials.

    This configuration supports the @anthropic/gmail-mcp package which requires
    OAuth2 credentials for Gmail API access.

    Attributes:
        client_id: OAuth2 client ID from Google Cloud Console.
        client_secret: OAuth2 client secret.
        refresh_token: OAuth2 refresh token for offline access.
        access_token: Current access token (optional, will be refreshed if expired).
        token_expiry: Timestamp when the access token expires.
        auth_type: Authentication type (oauth2 or service_account).
        service_account_file: Path to service account JSON file (for service_account auth).
        delegated_user: User email to impersonate (for service_account auth).
        scopes: OAuth2 scopes to request.
    """

    client_id: str = Field(..., description="OAuth2 client ID from Google Cloud Console")
    client_secret: SecretStr = Field(..., description="OAuth2 client secret")
    refresh_token: SecretStr = Field(..., description="OAuth2 refresh token for offline access")
    access_token: str | None = Field(None, description="Current access token")
    token_expiry: datetime | None = Field(None, description="Token expiry timestamp")
    auth_type: GmailAuthType = Field(GmailAuthType.OAUTH2, description="Authentication type")
    service_account_file: str | None = Field(
        None, description="Path to service account JSON file"
    )
    delegated_user: str | None = Field(
        None, description="User email to impersonate with service account"
    )
    scopes: list[str] = Field(
        default_factory=lambda: [
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/gmail.modify",
        ],
        description="OAuth2 scopes for Gmail API",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_id": "your-client-id.apps.googleusercontent.com",
                "client_secret": "your-client-secret",
                "refresh_token": "your-refresh-token",
                "auth_type": "oauth2",
                "scopes": [
                    "https://www.googleapis.com/auth/gmail.compose",
                    "https://www.googleapis.com/auth/gmail.modify",
                ],
            }
        }
    )

    @classmethod
    def from_env(cls) -> "GmailConfig":
        """Create config from environment variables.

        Expected environment variables:
            GMAIL_CLIENT_ID
            GMAIL_CLIENT_SECRET
            GMAIL_REFRESH_TOKEN
            GMAIL_ACCESS_TOKEN (optional)
        """
        import os

        return cls(
            client_id=os.environ["GMAIL_CLIENT_ID"],
            client_secret=SecretStr(os.environ["GMAIL_CLIENT_SECRET"]),
            refresh_token=SecretStr(os.environ["GMAIL_REFRESH_TOKEN"]),
            access_token=os.environ.get("GMAIL_ACCESS_TOKEN"),
        )


# =============================================================================
# Email Models
# =============================================================================


class Attachment(BaseModel):
    """Email attachment model.

    Attributes:
        filename: Name of the file with extension.
        content: Raw file content as bytes.
        mime_type: MIME type of the file (e.g., 'application/pdf').
        content_id: Optional Content-ID for inline images.
    """

    filename: str = Field(..., description="Filename with extension")
    content: bytes = Field(..., description="File content as bytes")
    mime_type: str = Field(default="application/octet-stream", description="MIME type")
    content_id: str | None = Field(None, description="Content-ID for inline attachments")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename doesn't contain path separators."""
        if "/" in v or "\\" in v:
            raise ValueError("Filename cannot contain path separators")
        return v

    @property
    def content_base64(self) -> str:
        """Return content encoded as URL-safe base64."""
        return base64.urlsafe_b64encode(self.content).decode("utf-8")

    @classmethod
    def from_file(cls, file_path: str | Path, mime_type: str | None = None) -> "Attachment":
        """Create attachment from a file path.

        Args:
            file_path: Path to the file.
            mime_type: Optional MIME type (auto-detected if not provided).

        Returns:
            Attachment instance.
        """
        path = Path(file_path)
        content = path.read_bytes()

        if mime_type is None:
            import mimetypes

            mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

        return cls(filename=path.name, content=content, mime_type=mime_type)

    @classmethod
    def from_pdf_bytes(cls, pdf_bytes: bytes, filename: str = "resume.pdf") -> "Attachment":
        """Create a PDF attachment from bytes.

        Args:
            pdf_bytes: PDF file content.
            filename: Filename to use.

        Returns:
            Attachment instance.
        """
        return cls(filename=filename, content=pdf_bytes, mime_type="application/pdf")


class EmailDraft(BaseModel):
    """Email draft content model.

    This model represents an email draft to be created in Gmail.
    The draft is created but NOT sent - users must manually review and send.

    Attributes:
        to: List of recipient email addresses.
        cc: List of CC recipient email addresses.
        bcc: List of BCC recipient email addresses.
        subject: Email subject line.
        body_text: Plain text body (optional if body_html provided).
        body_html: HTML formatted body (optional if body_text provided).
        attachments: List of file attachments.
        reply_to: Email address for replies.
        thread_id: Gmail thread ID if this is a reply.
        in_reply_to: Message-ID of the email being replied to.
        references: Message-IDs of previous emails in the thread.
        headers: Additional custom headers.
    """

    to: list[EmailStr] = Field(..., min_length=1, description="Recipient email addresses")
    cc: list[EmailStr] = Field(default_factory=list, description="CC recipients")
    bcc: list[EmailStr] = Field(default_factory=list, description="BCC recipients")
    subject: str = Field(..., min_length=1, max_length=998, description="Email subject")
    body_text: str | None = Field(None, description="Plain text body")
    body_html: str | None = Field(None, description="HTML formatted body")
    attachments: list[Attachment] = Field(default_factory=list, description="File attachments")
    reply_to: EmailStr | None = Field(None, description="Reply-to address")
    thread_id: str | None = Field(None, description="Gmail thread ID for replies")
    in_reply_to: str | None = Field(None, description="Message-ID being replied to")
    references: list[str] = Field(default_factory=list, description="Thread reference IDs")
    headers: dict[str, str] = Field(default_factory=dict, description="Custom headers")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "to": ["hiring@company.com"],
                "subject": "Application for Software Engineer Position",
                "body_html": "<p>Dear Hiring Manager,</p><p>I am writing to apply...</p>",
                "attachments": [],
            }
        }
    )

    @field_validator("body_text", "body_html")
    @classmethod
    def validate_body_content(cls, v: str | None) -> str | None:
        """Ensure body content is not just whitespace."""
        if v is not None and not v.strip():
            return None
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate that at least one body format is provided."""
        if not self.body_text and not self.body_html:
            raise ValueError("Either body_text or body_html must be provided")

    def get_body_text(self) -> str:
        """Get plain text body, converting from HTML if needed."""
        if self.body_text:
            return self.body_text

        if self.body_html:
            # Simple HTML to text conversion
            text = re.sub(r"<br\s*/?>", "\n", self.body_html)
            text = re.sub(r"</p>", "\n\n", text)
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"&nbsp;", " ", text)
            text = re.sub(r"&amp;", "&", text)
            text = re.sub(r"&lt;", "<", text)
            text = re.sub(r"&gt;", ">", text)
            return text.strip()

        return ""


class DraftCreationResult(BaseModel):
    """Result of draft creation operation.

    Attributes:
        success: Whether the draft was created successfully.
        draft_id: Gmail draft ID (for opening in Gmail).
        message_id: Gmail message ID.
        thread_id: Gmail thread ID.
        draft_url: URL to open the draft in Gmail web interface.
        error_code: Error code if creation failed.
        error_message: Human-readable error message if creation failed.
        created_at: Timestamp when the draft was created.
    """

    success: bool = Field(..., description="Whether draft creation succeeded")
    draft_id: str | None = Field(None, description="Gmail draft ID")
    message_id: str | None = Field(None, description="Gmail message ID")
    thread_id: str | None = Field(None, description="Gmail thread ID")
    draft_url: str | None = Field(None, description="URL to open draft in Gmail")
    error_code: str | None = Field(None, description="Error code if failed")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "draft_id": "r1234567890",
                "message_id": "msg-abc123",
                "thread_id": "thread-xyz789",
                "draft_url": "https://mail.google.com/mail/u/0/#drafts/r1234567890",
                "created_at": "2025-01-25T10:30:00Z",
            }
        }
    )

    @classmethod
    def success_result(
        cls,
        draft_id: str,
        message_id: str | None = None,
        thread_id: str | None = None,
    ) -> "DraftCreationResult":
        """Create a successful result."""
        return cls(
            success=True,
            draft_id=draft_id,
            message_id=message_id,
            thread_id=thread_id,
            draft_url=f"https://mail.google.com/mail/u/0/#drafts/{draft_id}",
        )

    @classmethod
    def error_result(cls, error_code: str, error_message: str) -> "DraftCreationResult":
        """Create an error result."""
        return cls(
            success=False,
            error_code=error_code,
            error_message=error_message,
        )


# =============================================================================
# Email Templates
# =============================================================================


class EmailTemplate(BaseModel):
    """Email template with variable substitution support.

    Templates support placeholder variables in the format ${variable_name}.
    Variables are substituted using Python's string.Template.

    Attributes:
        name: Template name for identification.
        subject_template: Subject line with ${variables}.
        body_html_template: HTML body with ${variables}.
        body_text_template: Plain text body with ${variables} (optional).
        default_variables: Default values for variables.
        required_variables: List of required variable names.
    """

    name: str = Field(..., description="Template name")
    subject_template: str = Field(..., description="Subject with ${variables}")
    body_html_template: str = Field(..., description="HTML body with ${variables}")
    body_text_template: str | None = Field(None, description="Plain text body with ${variables}")
    default_variables: dict[str, str] = Field(
        default_factory=dict, description="Default variable values"
    )
    required_variables: list[str] = Field(
        default_factory=list, description="Required variable names"
    )

    def render(self, variables: dict[str, str]) -> tuple[str, str, str | None]:
        """Render the template with provided variables.

        Args:
            variables: Dictionary of variable name to value mappings.

        Returns:
            Tuple of (subject, body_html, body_text).

        Raises:
            ValueError: If required variables are missing.
        """
        # Merge defaults with provided variables
        merged_vars = {**self.default_variables, **variables}

        # Check required variables
        missing = set(self.required_variables) - set(merged_vars.keys())
        if missing:
            raise ValueError(f"Missing required template variables: {missing}")

        # Render templates
        subject = Template(self.subject_template).safe_substitute(merged_vars)
        body_html = Template(self.body_html_template).safe_substitute(merged_vars)
        body_text = None
        if self.body_text_template:
            body_text = Template(self.body_text_template).safe_substitute(merged_vars)

        return subject, body_html, body_text

    def create_draft(
        self,
        to: list[str],
        variables: dict[str, str],
        attachments: list[Attachment] | None = None,
        **kwargs: Any,
    ) -> EmailDraft:
        """Create an EmailDraft from this template.

        Args:
            to: Recipient email addresses.
            variables: Template variable values.
            attachments: Optional attachments.
            **kwargs: Additional EmailDraft fields (cc, bcc, reply_to, etc.).

        Returns:
            EmailDraft instance.
        """
        subject, body_html, body_text = self.render(variables)
        return EmailDraft(
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            attachments=attachments or [],
            **kwargs,
        )


# Predefined templates for common outreach scenarios
OUTREACH_TEMPLATES = {
    "job_application": EmailTemplate(
        name="Job Application",
        subject_template="Application for ${job_title} Position at ${company}",
        body_html_template="""
<p>Dear ${hiring_manager_name},</p>

<p>I am writing to express my interest in the <strong>${job_title}</strong> position at <strong>${company}</strong>.</p>

<p>${custom_intro}</p>

<p>Key highlights from my background:</p>
<ul>
${key_highlights}
</ul>

<p>${custom_closing}</p>

<p>I have attached my resume for your review. I would welcome the opportunity to discuss how my skills and experience align with your team's needs.</p>

<p>Thank you for considering my application.</p>

<p>Best regards,<br>
${sender_name}<br>
${sender_email}<br>
${sender_phone}</p>
""",
        body_text_template="""
Dear ${hiring_manager_name},

I am writing to express my interest in the ${job_title} position at ${company}.

${custom_intro}

Key highlights from my background:
${key_highlights_text}

${custom_closing}

I have attached my resume for your review. I would welcome the opportunity to discuss how my skills and experience align with your team's needs.

Thank you for considering my application.

Best regards,
${sender_name}
${sender_email}
${sender_phone}
""",
        default_variables={
            "hiring_manager_name": "Hiring Manager",
            "custom_intro": "",
            "custom_closing": "",
        },
        required_variables=["job_title", "company", "sender_name", "sender_email"],
    ),
    "networking_intro": EmailTemplate(
        name="Networking Introduction",
        subject_template="Connecting: ${sender_name} - ${shared_interest}",
        body_html_template="""
<p>Hi ${recipient_name},</p>

<p>I hope this message finds you well. My name is ${sender_name}, and I came across your profile while ${discovery_context}.</p>

<p>${personalized_note}</p>

<p>I'm currently ${current_situation} and am very interested in ${area_of_interest}.</p>

<p>I would love to hear your perspective on ${specific_question}. Would you be open to a brief conversation?</p>

<p>Thank you for your time, and I look forward to connecting!</p>

<p>Best,<br>
${sender_name}<br>
${sender_title}</p>
""",
        default_variables={
            "discovery_context": "researching professionals in the field",
        },
        required_variables=[
            "recipient_name",
            "sender_name",
            "shared_interest",
            "area_of_interest",
        ],
    ),
    "follow_up": EmailTemplate(
        name="Application Follow-Up",
        subject_template="Following Up: ${job_title} Application - ${sender_name}",
        body_html_template="""
<p>Dear ${hiring_manager_name},</p>

<p>I hope this message finds you well. I wanted to follow up on my application for the <strong>${job_title}</strong> position that I submitted on ${application_date}.</p>

<p>I remain very enthusiastic about the opportunity to join ${company} and contribute to ${team_or_project}.</p>

<p>${additional_context}</p>

<p>Please let me know if you need any additional information from me. I am available for an interview at your earliest convenience.</p>

<p>Thank you for your time and consideration.</p>

<p>Best regards,<br>
${sender_name}<br>
${sender_email}</p>
""",
        default_variables={
            "hiring_manager_name": "Hiring Manager",
            "additional_context": "",
        },
        required_variables=["job_title", "company", "application_date", "sender_name", "sender_email"],
    ),
    "referral_request": EmailTemplate(
        name="Referral Request",
        subject_template="Referral Request: ${job_title} at ${company}",
        body_html_template="""
<p>Hi ${contact_name},</p>

<p>I hope you're doing well! ${personal_greeting}</p>

<p>I noticed that ${company} is hiring for a <strong>${job_title}</strong> position, and given ${connection_context}, I thought I would reach out.</p>

<p>Based on my experience with ${relevant_experience}, I believe I would be a strong fit for this role. Here's why:</p>
<ul>
${fit_reasons}
</ul>

<p>Would you be willing to provide a referral or connect me with the hiring team? I've attached my resume for your reference.</p>

<p>I completely understand if you're not able to, and I appreciate you considering this request.</p>

<p>Thank you so much!</p>

<p>Best,<br>
${sender_name}</p>
""",
        default_variables={
            "personal_greeting": "",
        },
        required_variables=[
            "contact_name",
            "company",
            "job_title",
            "connection_context",
            "relevant_experience",
            "sender_name",
        ],
    ),
}


# =============================================================================
# Gmail MCP Service Errors
# =============================================================================


class GmailMCPError(Exception):
    """Base exception for Gmail MCP errors."""

    def __init__(self, message: str, error_code: str = "GMAIL_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class GmailAuthError(GmailMCPError):
    """Authentication error with Gmail API."""

    def __init__(self, message: str):
        super().__init__(message, "AUTH_ERROR")


class GmailQuotaError(GmailMCPError):
    """Quota exceeded error."""

    def __init__(self, message: str = "Gmail API quota exceeded"):
        super().__init__(message, "QUOTA_EXCEEDED")


class GmailDraftError(GmailMCPError):
    """Error creating draft."""

    def __init__(self, message: str):
        super().__init__(message, "DRAFT_ERROR")


# =============================================================================
# Gmail MCP Service
# =============================================================================


class GmailMCPService:
    """Gmail MCP service for creating email drafts.

    This service integrates with the @anthropic/gmail-mcp package to create
    email drafts via the Gmail API. Drafts are created but NOT sent - users
    must manually review and send them from Gmail.

    Usage:
        config = GmailConfig(
            client_id="...",
            client_secret="...",
            refresh_token="...",
        )
        service = GmailMCPService(config)

        draft = EmailDraft(
            to=["recipient@example.com"],
            subject="Hello",
            body_html="<p>Hello World</p>",
        )
        result = await service.create_draft(draft)

        if result.success:
            print(f"Draft created: {result.draft_url}")
    """

    # Gmail API endpoints
    GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
    TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

    def __init__(self, config: GmailConfig):
        """Initialize the Gmail MCP service.

        Args:
            config: Gmail OAuth configuration.
        """
        self.config = config
        self._client: Any = None  # httpx.AsyncClient, lazy initialized
        self._access_token: str | None = config.access_token
        self._token_expiry: datetime | None = config.token_expiry

    async def _get_client(self) -> Any:
        """Get or create the HTTP client."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_valid_token(self) -> str:
        """Ensure we have a valid access token, refreshing if needed.

        Returns:
            Valid access token.

        Raises:
            GmailAuthError: If token refresh fails.
        """
        # Check if current token is valid
        if self._access_token and self._token_expiry:
            if datetime.utcnow() < self._token_expiry:
                return self._access_token

        # Refresh the token
        try:
            client = await self._get_client()
            response = await client.post(
                self.TOKEN_ENDPOINT,
                data={
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret.get_secret_value(),
                    "refresh_token": self.config.refresh_token.get_secret_value(),
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            token_data = response.json()

            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            from datetime import timedelta

            self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)

            logger.info("Successfully refreshed Gmail access token")
            return self._access_token

        except Exception as e:
            logger.error(f"Failed to refresh Gmail token: {e}")
            raise GmailAuthError(f"Failed to refresh access token: {e}")

    def _build_mime_message(self, draft: EmailDraft) -> str:
        """Build a MIME message from the EmailDraft.

        Args:
            draft: Email draft to convert.

        Returns:
            Base64 URL-safe encoded MIME message.
        """
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email.mime.application import MIMEApplication
        from email import encoders
        import email.utils

        # Determine if we need multipart
        has_attachments = len(draft.attachments) > 0
        has_both_bodies = draft.body_text and draft.body_html

        if has_attachments:
            # Use multipart/mixed for attachments
            msg = MIMEMultipart("mixed")

            if has_both_bodies:
                # Create alternative part for text/html
                alt_part = MIMEMultipart("alternative")
                alt_part.attach(MIMEText(draft.get_body_text(), "plain", "utf-8"))
                alt_part.attach(MIMEText(draft.body_html, "html", "utf-8"))
                msg.attach(alt_part)
            elif draft.body_html:
                msg.attach(MIMEText(draft.body_html, "html", "utf-8"))
            else:
                msg.attach(MIMEText(draft.get_body_text(), "plain", "utf-8"))

            # Add attachments
            for attachment in draft.attachments:
                part = MIMEBase(*attachment.mime_type.split("/", 1))
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{attachment.filename}"',
                )
                if attachment.content_id:
                    part.add_header("Content-ID", f"<{attachment.content_id}>")
                msg.attach(part)

        elif has_both_bodies:
            # Use multipart/alternative for text and HTML
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(draft.body_text, "plain", "utf-8"))
            msg.attach(MIMEText(draft.body_html, "html", "utf-8"))
        elif draft.body_html:
            msg = MIMEText(draft.body_html, "html", "utf-8")
        else:
            msg = MIMEText(draft.get_body_text(), "plain", "utf-8")

        # Set headers
        msg["To"] = ", ".join(draft.to)
        msg["Subject"] = draft.subject

        if draft.cc:
            msg["Cc"] = ", ".join(draft.cc)
        if draft.bcc:
            msg["Bcc"] = ", ".join(draft.bcc)
        if draft.reply_to:
            msg["Reply-To"] = draft.reply_to
        if draft.in_reply_to:
            msg["In-Reply-To"] = draft.in_reply_to
        if draft.references:
            msg["References"] = " ".join(draft.references)

        # Add custom headers
        for header, value in draft.headers.items():
            msg[header] = value

        # Generate Message-ID
        msg["Message-ID"] = email.utils.make_msgid()
        msg["Date"] = email.utils.formatdate(localtime=True)

        # Encode as base64 URL-safe
        raw_message = msg.as_bytes()
        return base64.urlsafe_b64encode(raw_message).decode("utf-8")

    async def create_draft(self, draft: EmailDraft) -> DraftCreationResult:
        """Create an email draft in Gmail.

        The draft is created but NOT sent. Users must manually review and send
        the draft from the Gmail interface.

        Args:
            draft: Email draft to create.

        Returns:
            DraftCreationResult with draft ID and status.
        """
        try:
            # Ensure valid token
            access_token = await self._ensure_valid_token()

            # Build MIME message
            raw_message = self._build_mime_message(draft)

            # Prepare request body
            body: dict[str, Any] = {
                "message": {
                    "raw": raw_message,
                }
            }

            # If replying to a thread, include thread ID
            if draft.thread_id:
                body["message"]["threadId"] = draft.thread_id

            # Create draft via Gmail API
            client = await self._get_client()
            response = await client.post(
                f"{self.GMAIL_API_BASE}/users/me/drafts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )

            if response.status_code == 401:
                # Token might have been invalidated, try to refresh once
                self._access_token = None
                access_token = await self._ensure_valid_token()
                response = await client.post(
                    f"{self.GMAIL_API_BASE}/users/me/drafts",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )

            if response.status_code == 429:
                raise GmailQuotaError()

            response.raise_for_status()
            draft_data = response.json()

            logger.info(f"Successfully created Gmail draft: {draft_data.get('id')}")

            return DraftCreationResult.success_result(
                draft_id=draft_data["id"],
                message_id=draft_data.get("message", {}).get("id"),
                thread_id=draft_data.get("message", {}).get("threadId"),
            )

        except GmailAuthError as e:
            logger.error(f"Gmail authentication error: {e}")
            return DraftCreationResult.error_result(e.error_code, e.message)
        except GmailQuotaError as e:
            logger.error(f"Gmail quota error: {e}")
            return DraftCreationResult.error_result(e.error_code, e.message)
        except Exception as e:
            logger.error(f"Failed to create Gmail draft: {e}")
            return DraftCreationResult.error_result("DRAFT_ERROR", str(e))

    async def create_draft_from_template(
        self,
        template_name: str,
        to: list[str],
        variables: dict[str, str],
        attachments: list[Attachment] | None = None,
        **kwargs: Any,
    ) -> DraftCreationResult:
        """Create a draft using a predefined template.

        Args:
            template_name: Name of the template (from OUTREACH_TEMPLATES).
            to: Recipient email addresses.
            variables: Template variable values.
            attachments: Optional attachments.
            **kwargs: Additional EmailDraft fields.

        Returns:
            DraftCreationResult with draft ID and status.

        Raises:
            ValueError: If template not found.
        """
        template = OUTREACH_TEMPLATES.get(template_name)
        if not template:
            available = ", ".join(OUTREACH_TEMPLATES.keys())
            raise ValueError(f"Template '{template_name}' not found. Available: {available}")

        draft = template.create_draft(to, variables, attachments, **kwargs)
        return await self.create_draft(draft)

    async def create_job_application_draft(
        self,
        to: list[str],
        job_title: str,
        company: str,
        sender_name: str,
        sender_email: str,
        sender_phone: str = "",
        hiring_manager_name: str = "Hiring Manager",
        key_highlights: list[str] | None = None,
        custom_intro: str = "",
        custom_closing: str = "",
        resume_bytes: bytes | None = None,
        resume_filename: str = "resume.pdf",
        **kwargs: Any,
    ) -> DraftCreationResult:
        """Create a job application email draft with resume attachment.

        This is a convenience method that uses the job_application template
        with common parameters for job applications.

        Args:
            to: Recipient email addresses.
            job_title: Title of the job position.
            company: Company name.
            sender_name: Applicant's name.
            sender_email: Applicant's email.
            sender_phone: Applicant's phone number.
            hiring_manager_name: Name of hiring manager (default: "Hiring Manager").
            key_highlights: List of bullet points highlighting qualifications.
            custom_intro: Custom introduction paragraph.
            custom_closing: Custom closing paragraph.
            resume_bytes: PDF resume content as bytes.
            resume_filename: Filename for the resume attachment.
            **kwargs: Additional EmailDraft fields (cc, bcc, etc.).

        Returns:
            DraftCreationResult with draft ID and status.
        """
        # Format key highlights
        if key_highlights:
            key_highlights_html = "\n".join(f"<li>{h}</li>" for h in key_highlights)
            key_highlights_text = "\n".join(f"- {h}" for h in key_highlights)
        else:
            key_highlights_html = ""
            key_highlights_text = ""

        variables = {
            "job_title": job_title,
            "company": company,
            "sender_name": sender_name,
            "sender_email": sender_email,
            "sender_phone": sender_phone,
            "hiring_manager_name": hiring_manager_name,
            "key_highlights": key_highlights_html,
            "key_highlights_text": key_highlights_text,
            "custom_intro": custom_intro,
            "custom_closing": custom_closing,
        }

        # Create attachments list
        attachments = []
        if resume_bytes:
            attachments.append(
                Attachment.from_pdf_bytes(resume_bytes, filename=resume_filename)
            )

        return await self.create_draft_from_template(
            "job_application",
            to=to,
            variables=variables,
            attachments=attachments,
            **kwargs,
        )

    async def get_draft(self, draft_id: str) -> dict[str, Any] | None:
        """Retrieve a draft by ID.

        Args:
            draft_id: Gmail draft ID.

        Returns:
            Draft data or None if not found.
        """
        try:
            access_token = await self._ensure_valid_token()
            client = await self._get_client()

            response = await client.get(
                f"{self.GMAIL_API_BASE}/users/me/drafts/{draft_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Failed to get draft {draft_id}: {e}")
            return None

    async def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft by ID.

        Args:
            draft_id: Gmail draft ID.

        Returns:
            True if deleted, False otherwise.
        """
        try:
            access_token = await self._ensure_valid_token()
            client = await self._get_client()

            response = await client.delete(
                f"{self.GMAIL_API_BASE}/users/me/drafts/{draft_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            return response.status_code in (200, 204)

        except Exception as e:
            logger.error(f"Failed to delete draft {draft_id}: {e}")
            return False

    async def list_drafts(self, max_results: int = 10) -> list[dict[str, Any]]:
        """List recent drafts.

        Args:
            max_results: Maximum number of drafts to return.

        Returns:
            List of draft metadata.
        """
        try:
            access_token = await self._ensure_valid_token()
            client = await self._get_client()

            response = await client.get(
                f"{self.GMAIL_API_BASE}/users/me/drafts",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"maxResults": max_results},
            )

            response.raise_for_status()
            return response.json().get("drafts", [])

        except Exception as e:
            logger.error(f"Failed to list drafts: {e}")
            return []


# =============================================================================
# Template Utilities
# =============================================================================


def render_template(
    template_name: str,
    variables: dict[str, str],
) -> tuple[str, str, str | None]:
    """Render a predefined template.

    Args:
        template_name: Name of the template from OUTREACH_TEMPLATES.
        variables: Dictionary of variable values.

    Returns:
        Tuple of (subject, body_html, body_text).

    Raises:
        ValueError: If template not found.
    """
    template = OUTREACH_TEMPLATES.get(template_name)
    if not template:
        available = ", ".join(OUTREACH_TEMPLATES.keys())
        raise ValueError(f"Template '{template_name}' not found. Available: {available}")

    return template.render(variables)


def list_available_templates() -> dict[str, dict[str, Any]]:
    """List all available email templates with their required variables.

    Returns:
        Dictionary mapping template names to their metadata.
    """
    return {
        name: {
            "name": template.name,
            "required_variables": template.required_variables,
            "default_variables": template.default_variables,
        }
        for name, template in OUTREACH_TEMPLATES.items()
    }


def encode_attachment_base64(content: bytes) -> str:
    """Encode attachment content as URL-safe base64.

    Args:
        content: Raw file bytes.

    Returns:
        Base64 encoded string.
    """
    return base64.urlsafe_b64encode(content).decode("utf-8")


def decode_attachment_base64(encoded: str) -> bytes:
    """Decode URL-safe base64 to bytes.

    Args:
        encoded: Base64 encoded string.

    Returns:
        Raw file bytes.
    """
    return base64.urlsafe_b64decode(encoded)
