"""Outreach Agent for generating personalized networking messages.

This agent:
1. Creates personalized LinkedIn connection notes (max 300 chars)
2. Drafts professional cold emails
3. Injects scheduling links (Calendly)
4. Stores messages as drafts for manual review and sending
"""

import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class UserContext(BaseModel):
    """User information for personalization."""
    name: str
    current_role: str | None = None
    current_company: str | None = None
    target_role: str | None = None
    years_experience: int = 0
    top_skills: list[str] = Field(default_factory=list)
    notable_achievement: str | None = None
    calendly_link: str | None = None


class ContactContext(BaseModel):
    """Contact information for personalization."""
    name: str
    title: str
    company: str
    linkedin_url: str | None = None
    email: str | None = None
    mutual_connections: int = 0
    shared_background: str | None = None  # e.g., same school, previous company


class JobContext(BaseModel):
    """Job context for application-related outreach."""
    title: str
    company: str
    job_url: str | None = None
    applied: bool = False
    match_score: float | None = None


class OutreachDraft(BaseModel):
    """Generated outreach message draft."""
    channel: str  # "linkedin" or "email"
    subject: str | None = None  # For email only
    message: str
    char_count: int
    personalization_notes: list[str] = Field(default_factory=list)
    suggested_follow_up_days: int = 7


class OutreachResult(BaseModel):
    """Result from outreach generation."""
    contact_name: str
    contact_company: str
    linkedin_draft: OutreachDraft | None = None
    email_draft: OutreachDraft | None = None
    generation_notes: str | None = None


class OutreachAgent:
    """Agent that generates personalized networking messages.

    Guidelines:
    - LinkedIn: Max 300 chars, genuine tone, specific connection point
    - Email: Professional, concise (3-4 paragraphs max), clear ask
    - Never pushy or salesy
    - Always include scheduling link if available
    - Personalize based on mutual connections, shared background, job context
    """

    LINKEDIN_MAX_CHARS = 300

    def __init__(self, llm_client: Any | None = None):
        """Initialize the outreach agent.

        Args:
            llm_client: LLM client for advanced personalization.
        """
        self._llm = llm_client

    async def run(
        self,
        user: UserContext,
        contact: ContactContext,
        job: JobContext | None = None,
        generate_linkedin: bool = True,
        generate_email: bool = True,
    ) -> OutreachResult:
        """Generate outreach drafts for a contact.

        Args:
            user: User context for personalization.
            contact: Contact to reach out to.
            job: Optional job context if application-related.
            generate_linkedin: Generate LinkedIn connection note.
            generate_email: Generate email draft.

        Returns:
            OutreachResult with drafted messages.
        """
        logger.info(f"OutreachAgent: Generating outreach for {contact.name} at {contact.company}")

        linkedin_draft = None
        email_draft = None

        if generate_linkedin:
            linkedin_draft = self._generate_linkedin_note(user, contact, job)

        if generate_email and contact.email:
            email_draft = self._generate_email(user, contact, job)

        return OutreachResult(
            contact_name=contact.name,
            contact_company=contact.company,
            linkedin_draft=linkedin_draft,
            email_draft=email_draft,
            generation_notes=self._get_personalization_summary(user, contact, job),
        )

    async def batch_generate(
        self,
        user: UserContext,
        contacts: list[ContactContext],
        job: JobContext | None = None,
    ) -> list[OutreachResult]:
        """Generate outreach for multiple contacts.

        Args:
            user: User context for personalization.
            contacts: List of contacts.
            job: Optional job context.

        Returns:
            List of outreach results.
        """
        results = []
        for contact in contacts:
            result = await self.run(user, contact, job)
            results.append(result)
        return results

    def _generate_linkedin_note(
        self,
        user: UserContext,
        contact: ContactContext,
        job: JobContext | None,
    ) -> OutreachDraft:
        """Generate a LinkedIn connection note (max 300 chars).

        Structure:
        1. Greeting + context (why connecting)
        2. Brief value/shared interest
        3. Soft ask
        """
        first_name = contact.name.split()[0]

        # Determine connection angle
        if job and job.applied:
            # Post-application follow-up
            message = (
                f"Hi {first_name}, I recently applied for the {job.title} role at {contact.company} "
                f"and would love to connect. With {user.years_experience}+ years in "
                f"{', '.join(user.top_skills[:2])}, I'm excited about the opportunity. "
                f"Would appreciate any insights you might share!"
            )
        elif job:
            # Pre-application interest
            message = (
                f"Hi {first_name}, I'm exploring {job.title} opportunities and noticed your work at {contact.company}. "
                f"As someone with experience in {', '.join(user.top_skills[:2])}, "
                f"I'd love to learn more about the team culture. Happy to connect!"
            )
        elif contact.shared_background:
            # Shared background connection
            message = (
                f"Hi {first_name}, noticed we share a background in {contact.shared_background}. "
                f"I'm currently a {user.current_role or 'professional'} exploring opportunities in "
                f"{user.target_role or 'the industry'}. Would love to connect and hear about your experience at {contact.company}!"
            )
        else:
            # General networking
            message = (
                f"Hi {first_name}, I came across your profile and was impressed by your work at {contact.company}. "
                f"As a {user.current_role or 'professional'} with {user.years_experience}+ years in "
                f"{', '.join(user.top_skills[:2])}, I'd value connecting and learning from your insights!"
            )

        # Truncate if needed
        if len(message) > self.LINKEDIN_MAX_CHARS:
            message = message[:self.LINKEDIN_MAX_CHARS - 3] + "..."

        return OutreachDraft(
            channel="linkedin",
            message=message,
            char_count=len(message),
            personalization_notes=self._get_personalization_points(user, contact, job),
            suggested_follow_up_days=7,
        )

    def _generate_email(
        self,
        user: UserContext,
        contact: ContactContext,
        job: JobContext | None,
    ) -> OutreachDraft:
        """Generate a professional cold email.

        Structure:
        1. Subject line (clear, specific)
        2. Opening (who you are, why reaching out)
        3. Value proposition (what you bring)
        4. Soft ask with scheduling link
        5. Sign-off
        """
        first_name = contact.name.split()[0]

        # Subject line
        if job:
            subject = f"Re: {job.title} opportunity at {contact.company}"
        else:
            subject = f"Quick question about {contact.company}"

        # Build email body
        lines = []

        # Opening
        lines.append(f"Hi {first_name},")
        lines.append("")

        if job and job.applied:
            lines.append(
                f"I recently applied for the {job.title} position at {contact.company} and wanted to reach out directly. "
                f"Your work as {contact.title} caught my attention, and I'd love the opportunity to connect."
            )
        elif job:
            lines.append(
                f"I came across the {job.title} role at {contact.company} and was genuinely excited by the opportunity. "
                f"As someone deeply passionate about {', '.join(user.top_skills[:2])}, I believe I could make a meaningful contribution."
            )
        else:
            lines.append(
                f"I hope this email finds you well. I'm reaching out because I've been following {contact.company}'s work "
                f"and would value the chance to connect with you."
            )
        lines.append("")

        # Value proposition
        if user.notable_achievement:
            lines.append(
                f"Quick background: {user.notable_achievement} "
                f"With {user.years_experience}+ years of experience, I'm now looking for my next challenge."
            )
        else:
            lines.append(
                f"I'm currently a {user.current_role or 'professional'} with {user.years_experience}+ years of experience "
                f"in {', '.join(user.top_skills[:3])}."
            )
        lines.append("")

        # Soft ask
        if user.calendly_link:
            lines.append(
                f"I'd love to chat for 15 minutes if you have time. Feel free to grab a slot here: {user.calendly_link}"
            )
        else:
            lines.append(
                "If you have 15 minutes for a quick call, I'd greatly appreciate the chance to learn from your experience."
            )
        lines.append("")

        # Sign-off
        lines.append("Thank you for considering,")
        lines.append(user.name)
        if user.current_role and user.current_company:
            lines.append(f"{user.current_role} at {user.current_company}")

        message = "\n".join(lines)

        return OutreachDraft(
            channel="email",
            subject=subject,
            message=message,
            char_count=len(message),
            personalization_notes=self._get_personalization_points(user, contact, job),
            suggested_follow_up_days=5,
        )

    def _get_personalization_points(
        self,
        user: UserContext,
        contact: ContactContext,
        job: JobContext | None,
    ) -> list[str]:
        """Get list of personalization points used."""
        points = []

        if job:
            points.append(f"Job context: {job.title} at {job.company}")
        if contact.shared_background:
            points.append(f"Shared background: {contact.shared_background}")
        if user.top_skills:
            points.append(f"Highlighted skills: {', '.join(user.top_skills[:3])}")
        if user.notable_achievement:
            points.append("Included notable achievement")
        if user.calendly_link:
            points.append("Included scheduling link")

        return points

    def _get_personalization_summary(
        self,
        user: UserContext,
        contact: ContactContext,
        job: JobContext | None,
    ) -> str:
        """Get a summary of how the message was personalized."""
        parts = [f"Outreach to {contact.name} ({contact.title})"]

        if job:
            parts.append(f"regarding {job.title} role")

        parts.append(f"highlighting {len(user.top_skills)} skills")

        return " ".join(parts)
