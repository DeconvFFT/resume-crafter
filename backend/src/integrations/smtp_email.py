"""Simple SMTP email service for sending outreach emails.

This is a simpler alternative to Gmail MCP OAuth - just uses standard SMTP
with email/password credentials.
"""

import logging
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, EmailStr, SecretStr

logger = logging.getLogger(__name__)


class SMTPConfig(BaseModel):
    """SMTP configuration."""

    host: str = "smtp.gmail.com"
    port: int = 587
    user: EmailStr
    password: SecretStr
    from_name: Optional[str] = None
    use_tls: bool = True

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """Load configuration from environment variables."""
        import os

        return cls(
            host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            port=int(os.getenv("SMTP_PORT", "587")),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            from_name=os.getenv("SMTP_FROM_NAME"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        )


class EmailAttachment(BaseModel):
    """Email attachment."""

    filename: str
    content: bytes
    mime_type: str = "application/octet-stream"

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_file(cls, file_path: str | Path) -> "EmailAttachment":
        """Create attachment from file path."""
        path = Path(file_path)
        with open(path, "rb") as f:
            content = f.read()

        # Detect mime type
        suffix = path.suffix.lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }
        mime_type = mime_types.get(suffix, "application/octet-stream")

        return cls(
            filename=path.name,
            content=content,
            mime_type=mime_type,
        )


class EmailMessage(BaseModel):
    """Email message to send."""

    to: list[EmailStr]
    subject: str
    body_text: str
    body_html: Optional[str] = None
    cc: Optional[list[EmailStr]] = None
    bcc: Optional[list[EmailStr]] = None
    reply_to: Optional[EmailStr] = None
    attachments: list[EmailAttachment] = []

    class Config:
        arbitrary_types_allowed = True


class SendResult(BaseModel):
    """Result of sending an email."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    recipients_sent: list[str] = []
    recipients_failed: list[str] = []


class SMTPEmailService:
    """Simple SMTP email service.

    Usage:
        config = SMTPConfig.from_env()
        service = SMTPEmailService(config)

        result = service.send(EmailMessage(
            to=["hiring@company.com"],
            subject="Application for Software Engineer",
            body_text="Hello...",
            attachments=[EmailAttachment.from_file("resume.pdf")],
        ))
    """

    def __init__(self, config: SMTPConfig):
        self.config = config

    def _create_message(self, email: EmailMessage) -> MIMEMultipart:
        """Create MIME message from EmailMessage."""
        msg = MIMEMultipart("mixed")

        # Headers
        from_addr = self.config.user
        if self.config.from_name:
            from_addr = f"{self.config.from_name} <{self.config.user}>"

        msg["From"] = from_addr
        msg["To"] = ", ".join(email.to)
        msg["Subject"] = email.subject

        if email.cc:
            msg["Cc"] = ", ".join(email.cc)
        if email.reply_to:
            msg["Reply-To"] = email.reply_to

        # Body
        body_part = MIMEMultipart("alternative")

        # Plain text
        body_part.attach(MIMEText(email.body_text, "plain", "utf-8"))

        # HTML (if provided)
        if email.body_html:
            body_part.attach(MIMEText(email.body_html, "html", "utf-8"))

        msg.attach(body_part)

        # Attachments
        for attachment in email.attachments:
            part = MIMEApplication(attachment.content, Name=attachment.filename)
            part["Content-Disposition"] = f'attachment; filename="{attachment.filename}"'
            msg.attach(part)

        return msg

    def send(self, email: EmailMessage) -> SendResult:
        """Send an email.

        Args:
            email: The email message to send.

        Returns:
            SendResult with success status and details.
        """
        try:
            msg = self._create_message(email)

            # All recipients
            all_recipients = list(email.to)
            if email.cc:
                all_recipients.extend(email.cc)
            if email.bcc:
                all_recipients.extend(email.bcc)

            # Connect and send
            context = ssl.create_default_context()

            with smtplib.SMTP(self.config.host, self.config.port) as server:
                if self.config.use_tls:
                    server.starttls(context=context)

                server.login(
                    self.config.user,
                    self.config.password.get_secret_value(),
                )

                # Send message
                refused = server.sendmail(
                    self.config.user,
                    all_recipients,
                    msg.as_string(),
                )

                # Track results
                recipients_sent = [r for r in all_recipients if r not in refused]
                recipients_failed = list(refused.keys()) if refused else []

                logger.info(
                    f"Email sent to {len(recipients_sent)} recipients, "
                    f"{len(recipients_failed)} failed"
                )

                return SendResult(
                    success=len(recipients_failed) == 0,
                    message_id=msg.get("Message-ID"),
                    recipients_sent=recipients_sent,
                    recipients_failed=recipients_failed,
                )

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return SendResult(
                success=False,
                error=f"Authentication failed: {e}",
            )
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return SendResult(
                success=False,
                error=f"SMTP error: {e}",
            )
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return SendResult(
                success=False,
                error=str(e),
            )

    def send_job_application(
        self,
        to: str,
        job_title: str,
        company: str,
        applicant_name: str,
        cover_letter: str,
        resume_path: Optional[str] = None,
        resume_bytes: Optional[bytes] = None,
    ) -> SendResult:
        """Convenience method to send a job application email.

        Args:
            to: Recipient email address.
            job_title: The job title being applied for.
            company: The company name.
            applicant_name: The applicant's name.
            cover_letter: The cover letter text.
            resume_path: Path to resume file (optional).
            resume_bytes: Resume content as bytes (optional).

        Returns:
            SendResult with success status.
        """
        attachments = []

        if resume_path:
            attachments.append(EmailAttachment.from_file(resume_path))
        elif resume_bytes:
            attachments.append(EmailAttachment(
                filename=f"{applicant_name.replace(' ', '_')}_Resume.pdf",
                content=resume_bytes,
                mime_type="application/pdf",
            ))

        email = EmailMessage(
            to=[to],
            subject=f"Application for {job_title} at {company}",
            body_text=cover_letter,
            body_html=f"<html><body><pre>{cover_letter}</pre></body></html>",
            attachments=attachments,
        )

        return self.send(email)

    def send_networking_outreach(
        self,
        to: str,
        recipient_name: str,
        sender_name: str,
        message: str,
        subject: Optional[str] = None,
    ) -> SendResult:
        """Convenience method to send a networking email.

        Args:
            to: Recipient email address.
            recipient_name: The recipient's name (for personalization).
            sender_name: The sender's name.
            message: The outreach message.
            subject: Optional custom subject line.

        Returns:
            SendResult with success status.
        """
        if not subject:
            subject = f"Connecting with you - {sender_name}"

        email = EmailMessage(
            to=[to],
            subject=subject,
            body_text=message,
        )

        return self.send(email)


# Global service instance
_smtp_service: Optional[SMTPEmailService] = None


def get_smtp_service() -> SMTPEmailService:
    """Get the global SMTP service instance."""
    global _smtp_service

    if _smtp_service is None:
        config = SMTPConfig.from_env()
        _smtp_service = SMTPEmailService(config)

    return _smtp_service


def configure_smtp_service(config: SMTPConfig) -> SMTPEmailService:
    """Configure and return the global SMTP service."""
    global _smtp_service
    _smtp_service = SMTPEmailService(config)
    return _smtp_service
