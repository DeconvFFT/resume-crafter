"""Base ATS form handler with abstract interface and common models."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ATSPlatform(str, Enum):
    """Supported ATS platforms."""

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    CUSTOM = "custom"


class FieldType(str, Enum):
    """Form field types."""

    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE = "file"
    DATE = "date"
    URL = "url"
    NUMBER = "number"
    HIDDEN = "hidden"


class FormField(BaseModel):
    """Represents a form field in an ATS application."""

    name: str = Field(..., description="Field name or identifier")
    field_type: FieldType = Field(..., description="Type of form field")
    label: str | None = Field(None, description="Human-readable label")
    required: bool = Field(False, description="Whether the field is required")
    selector: str | None = Field(None, description="CSS selector for the field")
    options: list[str] | None = Field(None, description="Options for select/radio fields")
    value: Any | None = Field(None, description="Current or default value")
    placeholder: str | None = Field(None, description="Placeholder text")
    validation_pattern: str | None = Field(None, description="Validation regex pattern")
    max_length: int | None = Field(None, description="Maximum input length")
    accepts: list[str] | None = Field(None, description="Accepted file types for file inputs")


class FormFieldMapping(BaseModel):
    """Maps user data to form fields."""

    first_name: str | None = None
    last_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    resume_path: str | None = None
    cover_letter_path: str | None = None
    cover_letter_text: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    github_url: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    location: str | None = None
    work_authorization: str | None = None
    salary_expectation: str | None = None
    start_date: str | None = None
    custom_answers: dict[str, Any] = Field(default_factory=dict)


class FormDetectionResult(BaseModel):
    """Result of ATS platform detection."""

    platform: ATSPlatform
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    url_pattern_matched: bool = False
    dom_pattern_matched: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class FormFillingResult(BaseModel):
    """Result of form filling operation."""

    success: bool
    fields_filled: list[str] = Field(default_factory=list)
    fields_failed: list[str] = Field(default_factory=list)
    fields_skipped: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    screenshot_path: str | None = None
    next_step_url: str | None = None
    requires_manual_intervention: bool = False
    intervention_reason: str | None = None


class BaseATSHandler(ABC):
    """Abstract base class for ATS form handlers."""

    platform: ATSPlatform

    def __init__(self):
        """Initialize the ATS handler."""
        self._browser = None
        self._playwright = None
        self._page = None

    async def _get_browser(self):
        """Get or create Playwright browser instance."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ],
                )
            except ImportError:
                raise ImportError(
                    "Playwright not installed. Install with: "
                    "pip install playwright && playwright install chromium"
                )
        return self._browser

    async def _get_page(self, url: str | None = None):
        """Get or create a new page, optionally navigating to URL."""
        browser = await self._get_browser()
        if self._page is None or self._page.is_closed():
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            self._page = await context.new_page()

        if url:
            await self._page.goto(url, wait_until="networkidle")

        return self._page

    async def close(self) -> None:
        """Close browser resources."""
        if self._page and not self._page.is_closed():
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    @abstractmethod
    async def detect_platform(self, url: str, html: str | None = None) -> FormDetectionResult:
        """Detect if a URL/page belongs to this ATS platform.

        Args:
            url: The application form URL.
            html: Optional HTML content of the page.

        Returns:
            FormDetectionResult with platform detection details.
        """
        pass

    @abstractmethod
    async def get_form_fields(self, url: str) -> list[FormField]:
        """Extract form fields from an application page.

        Args:
            url: The application form URL.

        Returns:
            List of FormField objects representing the form structure.
        """
        pass

    @abstractmethod
    async def fill_form(
        self,
        url: str,
        field_mapping: FormFieldMapping,
        submit: bool = False,
    ) -> FormFillingResult:
        """Fill out the application form with provided data.

        Args:
            url: The application form URL.
            field_mapping: User data mapped to form fields.
            submit: Whether to submit the form after filling.

        Returns:
            FormFillingResult with details of the operation.
        """
        pass

    async def _fill_text_field(self, selector: str, value: str) -> bool:
        """Fill a text input field."""
        try:
            page = await self._get_page()
            await page.fill(selector, value)
            return True
        except Exception:
            return False

    async def _select_option(self, selector: str, value: str) -> bool:
        """Select an option from a dropdown."""
        try:
            page = await self._get_page()
            await page.select_option(selector, value)
            return True
        except Exception:
            return False

    async def _upload_file(self, selector: str, file_path: str) -> bool:
        """Upload a file to a file input."""
        try:
            page = await self._get_page()
            await page.set_input_files(selector, file_path)
            return True
        except Exception:
            return False

    async def _click_element(self, selector: str) -> bool:
        """Click an element."""
        try:
            page = await self._get_page()
            await page.click(selector)
            return True
        except Exception:
            return False

    async def _wait_for_navigation(self, timeout: int = 30000) -> bool:
        """Wait for page navigation."""
        try:
            page = await self._get_page()
            await page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception:
            return False

    async def _take_screenshot(self, path: str) -> str | None:
        """Take a screenshot of the current page."""
        try:
            page = await self._get_page()
            await page.screenshot(path=path, full_page=True)
            return path
        except Exception:
            return None

    async def _get_page_html(self) -> str:
        """Get current page HTML content."""
        page = await self._get_page()
        return await page.content()

    async def _evaluate_js(self, script: str) -> Any:
        """Evaluate JavaScript on the page."""
        page = await self._get_page()
        return await page.evaluate(script)
