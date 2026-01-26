"""Application Form Agent for automating job applications.

This agent:
1. Detects application form type (Greenhouse, Lever, Workday, etc.)
2. Maps user profile data to form fields
3. Fills forms using Playwright automation
4. Handles file uploads (resume, cover letter)
5. Captures confirmation and updates application status

Note: Full Playwright integration will be implemented in Phase 6.
This is a scaffolding implementation that defines the interface.
"""

import logging
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ATSPlatform(str, Enum):
    """Known ATS platforms with specific form handlers."""
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    ASHBY = "ashby"
    ICIMS = "icims"
    TALEO = "taleo"
    SMARTRECRUITERS = "smartrecruiters"
    BAMBOOHR = "bamboohr"
    UNKNOWN = "unknown"


class FormField(BaseModel):
    """A detected form field."""
    name: str
    field_type: str  # text, email, phone, select, textarea, file, checkbox, radio
    label: str | None = None
    required: bool = False
    options: list[str] | None = None  # For select/radio fields
    value: str | None = None  # Filled value


class ApplicationFormData(BaseModel):
    """User data for filling application forms."""
    # Personal info
    first_name: str
    last_name: str
    email: str
    phone: str | None = None

    # Location
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zip_code: str | None = None

    # Links
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    github_url: str | None = None
    website_url: str | None = None

    # Documents
    resume_path: str | None = None
    cover_letter_text: str | None = None
    cover_letter_path: str | None = None

    # Work authorization
    authorized_to_work: bool = True
    requires_sponsorship: bool = False

    # Additional
    salary_expectation: int | None = None
    available_start_date: str | None = None
    years_of_experience: int | None = None

    # Custom answers (question -> answer)
    custom_answers: dict[str, str] = Field(default_factory=dict)


class FormDetectionResult(BaseModel):
    """Result of form detection."""
    platform: ATSPlatform
    confidence: float = Field(ge=0, le=1)
    form_url: str
    fields_detected: list[FormField] = Field(default_factory=list)
    requires_login: bool = False
    detection_notes: str | None = None


class FormFillingResult(BaseModel):
    """Result of form filling attempt."""
    success: bool
    platform: ATSPlatform
    fields_filled: list[str] = Field(default_factory=list)
    fields_failed: list[str] = Field(default_factory=list)
    fields_skipped: list[str] = Field(default_factory=list)
    confirmation_received: bool = False
    confirmation_text: str | None = None
    error_message: str | None = None
    screenshot_path: str | None = None  # Screenshot of final state


class ApplicationFormAgent:
    """Agent that automates job application form filling.

    Workflow:
    1. Navigate to application URL
    2. Detect ATS platform and form structure
    3. Map user data to form fields
    4. Fill form fields (with validation)
    5. Upload resume and cover letter
    6. Submit form (or save draft for review)
    7. Capture confirmation

    Supported platforms (with specific handlers):
    - Greenhouse (most common)
    - Lever
    - Workday (complex multi-step)
    - Generic forms

    Note: This is a scaffolding implementation. Playwright integration
    will be added in Phase 6 (Backend - Integrations).
    """

    # Field name patterns for auto-mapping
    FIELD_PATTERNS = {
        "first_name": ["first_name", "firstname", "first-name", "fname", "given_name"],
        "last_name": ["last_name", "lastname", "last-name", "lname", "surname", "family_name"],
        "email": ["email", "e-mail", "email_address"],
        "phone": ["phone", "telephone", "mobile", "phone_number", "cell"],
        "linkedin": ["linkedin", "linkedin_url", "linkedin_profile"],
        "resume": ["resume", "cv", "resume_file", "attachment"],
        "cover_letter": ["cover_letter", "cover", "coverletter", "letter"],
    }

    def __init__(self, headless: bool = True):
        """Initialize the application form agent.

        Args:
            headless: Run browser in headless mode.
        """
        self._headless = headless
        self._browser = None  # Playwright browser instance

    async def detect_form(
        self,
        url: str,
    ) -> FormDetectionResult:
        """Detect form type and structure at a URL.

        Args:
            url: Application form URL.

        Returns:
            FormDetectionResult with platform and detected fields.
        """
        logger.info(f"ApplicationFormAgent: Detecting form at {url}")

        # Detect platform from URL
        platform = self._detect_platform_from_url(url)

        # Mock field detection (real implementation in Phase 6)
        fields = self._get_standard_fields(platform)

        return FormDetectionResult(
            platform=platform,
            confidence=0.9 if platform != ATSPlatform.UNKNOWN else 0.5,
            form_url=url,
            fields_detected=fields,
            requires_login=False,
            detection_notes=f"Detected as {platform.value} based on URL pattern",
        )

    async def fill_form(
        self,
        url: str,
        form_data: ApplicationFormData,
        submit: bool = False,
    ) -> FormFillingResult:
        """Fill an application form.

        Args:
            url: Application form URL.
            form_data: User data for filling.
            submit: Whether to submit (False = save draft for review).

        Returns:
            FormFillingResult with success status and details.
        """
        logger.info(f"ApplicationFormAgent: Filling form at {url}")

        # Detect form first
        detection = await self.detect_form(url)

        # Map fields to data
        field_mapping = self._map_fields_to_data(detection.fields_detected, form_data)

        # Mock filling (real implementation in Phase 6)
        filled_fields = []
        failed_fields = []
        skipped_fields = []

        for field in detection.fields_detected:
            if field.name in field_mapping:
                field.value = field_mapping[field.name]
                filled_fields.append(field.name)
            elif field.required:
                failed_fields.append(field.name)
            else:
                skipped_fields.append(field.name)

        success = len(failed_fields) == 0

        return FormFillingResult(
            success=success,
            platform=detection.platform,
            fields_filled=filled_fields,
            fields_failed=failed_fields,
            fields_skipped=skipped_fields,
            confirmation_received=success and submit,
            confirmation_text="Application submitted successfully" if success and submit else None,
            error_message=f"Missing required fields: {failed_fields}" if failed_fields else None,
        )

    async def upload_resume(
        self,
        file_path: str,
    ) -> bool:
        """Upload resume file to form.

        Args:
            file_path: Path to resume file.

        Returns:
            True if upload successful.
        """
        logger.info(f"ApplicationFormAgent: Uploading resume from {file_path}")
        # Mock implementation
        return True

    def _detect_platform_from_url(self, url: str) -> ATSPlatform:
        """Detect ATS platform from URL patterns."""
        url_lower = url.lower()

        if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
            return ATSPlatform.GREENHOUSE
        elif "lever.co" in url_lower or "jobs.lever" in url_lower:
            return ATSPlatform.LEVER
        elif "myworkday" in url_lower or "workday.com" in url_lower:
            return ATSPlatform.WORKDAY
        elif "ashbyhq.com" in url_lower:
            return ATSPlatform.ASHBY
        elif "icims.com" in url_lower:
            return ATSPlatform.ICIMS
        elif "taleo" in url_lower:
            return ATSPlatform.TALEO
        elif "smartrecruiters" in url_lower:
            return ATSPlatform.SMARTRECRUITERS
        elif "bamboohr" in url_lower:
            return ATSPlatform.BAMBOOHR
        else:
            return ATSPlatform.UNKNOWN

    def _get_standard_fields(self, platform: ATSPlatform) -> list[FormField]:
        """Get standard fields for a platform."""
        # Common fields across platforms
        standard_fields = [
            FormField(name="first_name", field_type="text", label="First Name", required=True),
            FormField(name="last_name", field_type="text", label="Last Name", required=True),
            FormField(name="email", field_type="email", label="Email", required=True),
            FormField(name="phone", field_type="phone", label="Phone", required=False),
            FormField(name="resume", field_type="file", label="Resume/CV", required=True),
            FormField(name="linkedin_url", field_type="text", label="LinkedIn Profile", required=False),
        ]

        # Platform-specific additions
        if platform == ATSPlatform.GREENHOUSE:
            standard_fields.extend([
                FormField(name="cover_letter", field_type="textarea", label="Cover Letter", required=False),
                FormField(name="authorized_to_work", field_type="checkbox", label="Authorized to work", required=True),
            ])
        elif platform == ATSPlatform.WORKDAY:
            standard_fields.extend([
                FormField(name="address", field_type="text", label="Address", required=True),
                FormField(name="city", field_type="text", label="City", required=True),
                FormField(name="country", field_type="select", label="Country", required=True),
            ])

        return standard_fields

    def _map_fields_to_data(
        self,
        fields: list[FormField],
        data: ApplicationFormData,
    ) -> dict[str, str]:
        """Map form fields to user data."""
        mapping = {}

        data_dict = data.model_dump()

        for field in fields:
            # Direct match
            if field.name in data_dict and data_dict[field.name]:
                mapping[field.name] = str(data_dict[field.name])
                continue

            # Pattern matching
            for data_key, patterns in self.FIELD_PATTERNS.items():
                if field.name.lower() in patterns and data_key in data_dict and data_dict[data_key]:
                    mapping[field.name] = str(data_dict[data_key])
                    break

        return mapping

    async def close(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
