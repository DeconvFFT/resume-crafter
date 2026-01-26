"""Automation agents for job search and networking workflows.

This package provides agents for automating:
- Job discovery across multiple platforms (LinkedIn, Indeed, Greenhouse, etc.)
- Job qualification and match scoring
- Application form filling with Playwright automation
- Contact discovery at target companies
- Personalized outreach message generation (LinkedIn and email)

Note: Playwright integration for ApplicationFormAgent will be implemented in Phase 6.
"""

from .application_form_agent import (
    ApplicationFormAgent,
    ApplicationFormData,
    ATSPlatform,
    FormDetectionResult,
    FormField,
    FormFillingResult,
)
from .contact_discovery_agent import (
    ContactDiscoveryAgent,
    ContactDiscoveryResult,
    ContactInfo,
)
from .job_discovery_agent import (
    DiscoveredJobData,
    JobDiscoveryAgent,
    JobDiscoveryResult,
    JobSearchQuery,
)
from .job_qualification_agent import (
    ExperienceMatch,
    JobQualificationAgent,
    JobRequirements,
    QualificationResult,
    SkillMatch,
    UserProfile,
)
from .outreach_agent import (
    ContactContext,
    JobContext,
    OutreachAgent,
    OutreachDraft,
    OutreachResult,
    UserContext,
)

__all__ = [
    # Job Discovery Agent
    "JobDiscoveryAgent",
    "JobSearchQuery",
    "DiscoveredJobData",
    "JobDiscoveryResult",
    # Job Qualification Agent
    "JobQualificationAgent",
    "JobRequirements",
    "UserProfile",
    "QualificationResult",
    "SkillMatch",
    "ExperienceMatch",
    # Application Form Agent
    "ApplicationFormAgent",
    "ATSPlatform",
    "FormField",
    "ApplicationFormData",
    "FormDetectionResult",
    "FormFillingResult",
    # Contact Discovery Agent
    "ContactDiscoveryAgent",
    "ContactInfo",
    "ContactDiscoveryResult",
    # Outreach Agent
    "OutreachAgent",
    "UserContext",
    "ContactContext",
    "JobContext",
    "OutreachDraft",
    "OutreachResult",
]
