"""Workday ATS form handler."""

import re
from typing import Any

from pydantic import BaseModel, Field

from .base import (
    ATSPlatform,
    BaseATSHandler,
    FieldType,
    FormDetectionResult,
    FormField,
    FormFieldMapping,
    FormFillingResult,
)


class WorkdayAuthConfig(BaseModel):
    """Authentication configuration for Workday."""

    email: str | None = None
    password: str | None = None
    use_sso: bool = False
    sso_provider: str | None = None


class WorkdayPageState(BaseModel):
    """Represents current state in Workday multi-page workflow."""

    current_page: int = 1
    total_pages: int | None = None
    page_title: str | None = None
    requires_auth: bool = False
    is_authenticated: bool = False
    has_errors: bool = False
    error_messages: list[str] = Field(default_factory=list)


class WorkdayHandler(BaseATSHandler):
    """Handler for Workday ATS forms (myworkdayjobs.com)."""

    platform = ATSPlatform.WORKDAY

    # URL patterns for Workday
    URL_PATTERNS = [
        r"myworkdayjobs\.com",
        r"workday\.com.*?/apply",
        r"\.wd\d+\.myworkdayjobs\.com",
        r"workdayjobs\.com",
    ]

    # CSS selectors for Workday forms
    SELECTORS = {
        "form": "form, [data-automation-id='applicationForm'], .css-1n5u5pb",
        "first_name": "[data-automation-id='legalNameSection_firstName'], input[id*='firstName']",
        "last_name": "[data-automation-id='legalNameSection_lastName'], input[id*='lastName']",
        "email": "[data-automation-id='email'], input[type='email']",
        "phone": "[data-automation-id='phone'], input[type='tel']",
        "address": "[data-automation-id='addressSection']",
        "resume": "[data-automation-id='resume'], input[type='file']",
        "cover_letter": "[data-automation-id='coverLetter']",
        "linkedin": "[data-automation-id='linkedinUrl'], input[name*='linkedin']",
        "submit": "[data-automation-id='submitButton'], button[type='submit']",
        "next": "[data-automation-id='nextButton'], button[data-automation-id='bottom-navigation-next-button']",
        "previous": "[data-automation-id='previousButton'], button[data-automation-id='bottom-navigation-previous-button']",
        "save": "[data-automation-id='saveButton']",
        "login_email": "[data-automation-id='email'], input[name='username']",
        "login_password": "[data-automation-id='password'], input[name='password']",
        "login_submit": "[data-automation-id='signInSubmitButton'], button[type='submit']",
        "create_account": "[data-automation-id='createAccountLink']",
        "sso_button": "[data-automation-id='ssoButton'], .sso-link",
        "error_message": "[data-automation-id='errorMessage'], .css-1mc5sp4, .error-message",
        "page_indicator": "[data-automation-id='pageIndicator'], .css-1a9hjgz",
    }

    # Workday uses a multi-page application workflow
    WORKFLOW_PAGES = [
        "my_information",
        "my_experience",
        "application_questions",
        "voluntary_disclosures",
        "self_identify",
        "review",
    ]

    def __init__(self, auth_config: WorkdayAuthConfig | None = None):
        """Initialize Workday handler with optional auth config."""
        super().__init__()
        self.auth_config = auth_config
        self._page_state = WorkdayPageState()

    async def detect_platform(self, url: str, html: str | None = None) -> FormDetectionResult:
        """Detect if URL belongs to Workday."""
        url_matched = any(re.search(pattern, url, re.IGNORECASE) for pattern in self.URL_PATTERNS)
        dom_matched = False
        confidence = 0.0
        metadata = {}

        if url_matched:
            confidence = 0.9

        if html:
            # Check for Workday-specific DOM elements and attributes
            workday_indicators = [
                "workday",
                "data-automation-id",
                "css-1n5u5pb",  # Workday's CSS class pattern
                "wd-application",
                "myworkday",
            ]
            for indicator in workday_indicators:
                if indicator.lower() in html.lower():
                    dom_matched = True
                    confidence = min(confidence + 0.05, 1.0)

            # Check for authentication requirement
            if any(
                pattern in html.lower()
                for pattern in ["sign in", "create account", "signinsection", "login"]
            ):
                metadata["requires_auth"] = True

            # Try to detect current page in workflow
            for page in self.WORKFLOW_PAGES:
                if page.replace("_", " ") in html.lower() or page in html.lower():
                    metadata["detected_page"] = page
                    break

            # Extract job requisition ID if present
            req_id_match = re.search(
                r"requisition[_-]?id[=:]\s*['\"]?([A-Z0-9-]+)", html, re.IGNORECASE
            )
            if req_id_match:
                metadata["requisition_id"] = req_id_match.group(1)

        return FormDetectionResult(
            platform=self.platform,
            confidence=confidence,
            url_pattern_matched=url_matched,
            dom_pattern_matched=dom_matched,
            metadata=metadata,
        )

    async def get_form_fields(self, url: str) -> list[FormField]:
        """Extract form fields from Workday application page."""
        fields = []

        try:
            page = await self._get_page(url)

            # Wait for page to load
            await page.wait_for_load_state("networkidle", timeout=15000)

            # Check if authentication is required
            auth_required = await self._check_auth_required(page)
            if auth_required:
                if not await self._handle_authentication(page):
                    # Return fields indicating auth is needed
                    return [
                        FormField(
                            name="_auth_required",
                            field_type=FieldType.TEXT,
                            label="Authentication Required",
                            required=True,
                        )
                    ]

            # Collect fields from all pages
            all_fields = []
            visited_pages = set()

            while True:
                current_url = page.url
                if current_url in visited_pages:
                    break
                visited_pages.add(current_url)

                # Update page state
                await self._update_page_state(page)

                # Extract fields from current page
                page_fields = await self._extract_page_fields(page)
                all_fields.extend(page_fields)

                # Try to navigate to next page
                next_button = await page.query_selector(self.SELECTORS["next"])
                if next_button and await next_button.is_visible() and await next_button.is_enabled():
                    # Don't actually click in get_form_fields to avoid side effects
                    # Just note that more pages exist
                    break
                else:
                    break

            # Convert to FormField objects
            for data in all_fields:
                field_type = self._map_field_type(data.get("type", "text"))
                options = None
                if data.get("options"):
                    options = [opt.get("text", opt.get("value", "")) for opt in data["options"]]

                fields.append(
                    FormField(
                        name=data.get("name", ""),
                        field_type=field_type,
                        label=data.get("label"),
                        required=data.get("required", False),
                        selector=data.get("selector"),
                        options=options,
                        value=data.get("value"),
                        placeholder=data.get("placeholder"),
                    )
                )

        except Exception as e:
            pass

        return fields

    async def _check_auth_required(self, page) -> bool:
        """Check if the page requires authentication."""
        login_indicators = [
            self.SELECTORS["login_email"],
            self.SELECTORS["login_password"],
            "[data-automation-id='signInSection']",
            ".sign-in-form",
        ]

        for selector in login_indicators:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                return True

        return False

    async def _handle_authentication(self, page) -> bool:
        """Handle Workday authentication if credentials are configured."""
        if not self.auth_config:
            self._page_state.requires_auth = True
            return False

        try:
            if self.auth_config.use_sso and self.auth_config.sso_provider:
                # Handle SSO login
                sso_button = await page.query_selector(self.SELECTORS["sso_button"])
                if sso_button:
                    await sso_button.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    # SSO will redirect, check if we're authenticated
                    # This is provider-specific and may need manual intervention
                    self._page_state.requires_auth = True
                    return False
            else:
                # Handle email/password login
                if self.auth_config.email and self.auth_config.password:
                    email_input = await page.query_selector(self.SELECTORS["login_email"])
                    password_input = await page.query_selector(self.SELECTORS["login_password"])

                    if email_input and password_input:
                        await email_input.fill(self.auth_config.email)
                        await password_input.fill(self.auth_config.password)

                        submit_button = await page.query_selector(self.SELECTORS["login_submit"])
                        if submit_button:
                            await submit_button.click()
                            await page.wait_for_load_state("networkidle", timeout=15000)

                            # Check for error messages
                            error = await page.query_selector(self.SELECTORS["error_message"])
                            if error and await error.is_visible():
                                error_text = await error.text_content()
                                self._page_state.has_errors = True
                                self._page_state.error_messages.append(error_text or "Login failed")
                                return False

                            self._page_state.is_authenticated = True
                            return True

            return False

        except Exception as e:
            self._page_state.has_errors = True
            self._page_state.error_messages.append(f"Authentication error: {str(e)}")
            return False

    async def _update_page_state(self, page) -> None:
        """Update the current page state."""
        try:
            # Try to get page indicator
            page_indicator = await page.query_selector(self.SELECTORS["page_indicator"])
            if page_indicator:
                indicator_text = await page_indicator.text_content()
                if indicator_text:
                    # Parse "Step X of Y" or similar
                    match = re.search(r"(\d+)\s*(?:of|/)\s*(\d+)", indicator_text)
                    if match:
                        self._page_state.current_page = int(match.group(1))
                        self._page_state.total_pages = int(match.group(2))

            # Get page title
            page_title = await page.query_selector("h1, h2, [data-automation-id='pageTitle']")
            if page_title:
                self._page_state.page_title = await page_title.text_content()

        except Exception:
            pass

    async def _extract_page_fields(self, page) -> list[dict[str, Any]]:
        """Extract form fields from current Workday page."""
        return await page.evaluate(
            """
            () => {
                const fields = [];
                const form = document.querySelector('form, [data-automation-id="applicationForm"]');
                const container = form || document.body;

                // Find all input elements with Workday's data-automation-id
                const inputs = container.querySelectorAll(
                    'input:not([type="hidden"]):not([type="submit"]), textarea, select, [data-automation-id]'
                );

                const processedNames = new Set();

                inputs.forEach(input => {
                    // Skip if already processed or is a button
                    const automationId = input.getAttribute('data-automation-id') || '';
                    const name = input.name || input.id || automationId;

                    if (!name || processedNames.has(name)) return;
                    if (input.type === 'submit' || input.type === 'button') return;

                    processedNames.add(name);

                    const field = {
                        name: name,
                        automationId: automationId,
                        type: input.type || input.tagName.toLowerCase(),
                        id: input.id || '',
                        required: input.required || input.getAttribute('aria-required') === 'true',
                        placeholder: input.placeholder || '',
                        value: input.value || '',
                        options: [],
                    };

                    // Get label - Workday uses various label patterns
                    let label = '';
                    const labelEl = document.querySelector(`label[for="${input.id}"]`);
                    if (labelEl) {
                        label = labelEl.textContent.trim();
                    } else {
                        // Check parent for label
                        const parent = input.closest('[data-automation-id$="Section"], .css-1xj3a2o, .form-group');
                        if (parent) {
                            const parentLabel = parent.querySelector('label, [data-automation-id$="Label"]');
                            if (parentLabel) label = parentLabel.textContent.trim();
                        }
                    }
                    field.label = label;

                    // Handle select/dropdown
                    if (input.tagName === 'SELECT') {
                        const options = input.querySelectorAll('option');
                        field.options = Array.from(options).map(opt => ({
                            value: opt.value,
                            text: opt.textContent.trim()
                        }));
                    }

                    // Handle Workday custom dropdowns (they use divs)
                    if (automationId && automationId.includes('dropdown')) {
                        const optionContainer = input.closest('[data-automation-id]')
                            ?.querySelector('[data-automation-id*="optionList"]');
                        if (optionContainer) {
                            const options = optionContainer.querySelectorAll('[data-automation-id*="option"]');
                            field.options = Array.from(options).map(opt => ({
                                value: opt.getAttribute('data-value') || opt.textContent.trim(),
                                text: opt.textContent.trim()
                            }));
                        }
                    }

                    // Build selector
                    if (automationId) {
                        field.selector = `[data-automation-id="${automationId}"]`;
                    } else if (input.id) {
                        field.selector = '#' + CSS.escape(input.id);
                    } else if (input.name) {
                        field.selector = `[name="${CSS.escape(input.name)}"]`;
                    }

                    fields.push(field);
                });

                return fields;
            }
        """
        )

    async def fill_form(
        self,
        url: str,
        field_mapping: FormFieldMapping,
        submit: bool = False,
    ) -> FormFillingResult:
        """Fill out Workday application form, handling multi-page workflow."""
        filled = []
        failed = []
        skipped = []
        errors = []

        try:
            page = await self._get_page(url)
            await page.wait_for_load_state("networkidle", timeout=15000)

            # Handle authentication if required
            if await self._check_auth_required(page):
                if not await self._handle_authentication(page):
                    return FormFillingResult(
                        success=False,
                        errors=["Authentication required but not configured or failed"],
                        requires_manual_intervention=True,
                        intervention_reason="Please log in to Workday manually",
                    )

            # Process all pages in the workflow
            max_pages = 10
            current_page = 0

            while current_page < max_pages:
                current_page += 1
                await self._update_page_state(page)

                # Fill fields on current page
                page_result = await self._fill_page_fields(page, field_mapping)
                filled.extend(page_result["filled"])
                failed.extend(page_result["failed"])
                skipped.extend(page_result["skipped"])
                errors.extend(page_result["errors"])

                # Check for next button and proceed
                next_button = await page.query_selector(self.SELECTORS["next"])
                if next_button and await next_button.is_visible() and await next_button.is_enabled():
                    await next_button.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)

                    # Check for validation errors
                    error_el = await page.query_selector(self.SELECTORS["error_message"])
                    if error_el and await error_el.is_visible():
                        error_text = await error_el.text_content()
                        errors.append(f"Validation error on page {current_page}: {error_text}")
                        # Don't break, try to continue
                else:
                    break

            # Submit if requested and we're on the last page
            next_step_url = None
            if submit:
                try:
                    submit_button = await page.query_selector(self.SELECTORS["submit"])
                    if submit_button and await submit_button.is_visible():
                        await submit_button.click()
                        await page.wait_for_load_state("networkidle", timeout=30000)
                        next_step_url = page.url

                        # Check for success or error
                        error_el = await page.query_selector(self.SELECTORS["error_message"])
                        if error_el and await error_el.is_visible():
                            error_text = await error_el.text_content()
                            errors.append(f"Submission error: {error_text}")
                except Exception as e:
                    errors.append(f"Failed to submit form: {str(e)}")

            return FormFillingResult(
                success=len(failed) == 0 and len(errors) == 0,
                fields_filled=filled,
                fields_failed=failed,
                fields_skipped=skipped,
                errors=errors,
                next_step_url=next_step_url,
                requires_manual_intervention=len(failed) > 0 or len(errors) > 0,
                intervention_reason=(
                    "Some fields could not be filled or validation errors occurred"
                    if failed or errors
                    else None
                ),
            )

        except Exception as e:
            return FormFillingResult(
                success=False,
                fields_filled=filled,
                fields_failed=failed,
                fields_skipped=skipped,
                errors=[f"Form filling failed: {str(e)}"],
                requires_manual_intervention=True,
                intervention_reason=str(e),
            )

    async def _fill_page_fields(
        self, page, field_mapping: FormFieldMapping
    ) -> dict[str, list[str]]:
        """Fill fields on current Workday page."""
        result = {"filled": [], "failed": [], "skipped": [], "errors": []}

        # Map Workday automation IDs to field values
        field_selectors = [
            (self.SELECTORS["first_name"], field_mapping.first_name, "first_name"),
            (self.SELECTORS["last_name"], field_mapping.last_name, "last_name"),
            (self.SELECTORS["email"], field_mapping.email, "email"),
            (self.SELECTORS["phone"], field_mapping.phone, "phone"),
            (self.SELECTORS["linkedin"], field_mapping.linkedin_url, "linkedin"),
        ]

        # Fill standard text fields
        for selector, value, field_name in field_selectors:
            if not value:
                result["skipped"].append(field_name)
                continue

            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    # Clear existing value first
                    await element.fill("")
                    await element.fill(value)
                    result["filled"].append(field_name)
                else:
                    result["skipped"].append(field_name)
            except Exception as e:
                result["failed"].append(field_name)
                result["errors"].append(f"Failed to fill {field_name}: {str(e)}")

        # Handle resume upload
        if field_mapping.resume_path:
            try:
                resume_input = await page.query_selector(self.SELECTORS["resume"])
                if resume_input:
                    await resume_input.set_input_files(field_mapping.resume_path)
                    result["filled"].append("resume")
                else:
                    # Workday often has custom upload buttons
                    upload_button = await page.query_selector(
                        "[data-automation-id='uploadButton'], [data-automation-id='file-upload-input-ref']"
                    )
                    if upload_button:
                        async with page.expect_file_chooser() as fc_info:
                            await upload_button.click()
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(field_mapping.resume_path)
                        result["filled"].append("resume")
                    else:
                        result["skipped"].append("resume")
            except Exception as e:
                result["failed"].append("resume")
                result["errors"].append(f"Failed to upload resume: {str(e)}")

        # Handle cover letter
        if field_mapping.cover_letter_path or field_mapping.cover_letter_text:
            try:
                cover_input = await page.query_selector(self.SELECTORS["cover_letter"])
                if cover_input and await cover_input.is_visible():
                    tag_name = await cover_input.evaluate("el => el.tagName.toLowerCase()")
                    if tag_name == "textarea" and field_mapping.cover_letter_text:
                        await cover_input.fill(field_mapping.cover_letter_text)
                        result["filled"].append("cover_letter")
                    elif tag_name == "input" and field_mapping.cover_letter_path:
                        await cover_input.set_input_files(field_mapping.cover_letter_path)
                        result["filled"].append("cover_letter")
                    else:
                        result["skipped"].append("cover_letter")
                else:
                    result["skipped"].append("cover_letter")
            except Exception as e:
                result["failed"].append("cover_letter")
                result["errors"].append(f"Failed to fill cover letter: {str(e)}")

        # Handle location/address
        if field_mapping.location:
            try:
                address_section = await page.query_selector(self.SELECTORS["address"])
                if address_section:
                    # Workday address fields are complex, try to find city field
                    city_input = await address_section.query_selector(
                        "input[data-automation-id*='city'], input[name*='city']"
                    )
                    if city_input:
                        await city_input.fill(field_mapping.location)
                        result["filled"].append("location")
                    else:
                        result["skipped"].append("location")
                else:
                    result["skipped"].append("location")
            except Exception as e:
                result["failed"].append("location")
                result["errors"].append(f"Failed to fill location: {str(e)}")

        # Handle custom answers
        for question_id, answer in field_mapping.custom_answers.items():
            try:
                selectors_to_try = [
                    f"[data-automation-id='{question_id}']",
                    f"#{question_id}",
                    f"[name='{question_id}']",
                ]
                filled_custom = False
                for sel in selectors_to_try:
                    element = await page.query_selector(sel)
                    if element and await element.is_visible():
                        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                        input_type = await element.evaluate("el => el.type || ''")

                        if tag_name == "select":
                            await element.select_option(str(answer))
                        elif input_type == "radio":
                            radio_option = await page.query_selector(
                                f"input[name='{question_id}'][value='{answer}']"
                            )
                            if radio_option:
                                await radio_option.click()
                        elif input_type == "checkbox":
                            if answer in (True, "true", "yes", "1"):
                                await element.check()
                            else:
                                await element.uncheck()
                        else:
                            await element.fill(str(answer))

                        result["filled"].append(f"custom_{question_id}")
                        filled_custom = True
                        break

                if not filled_custom:
                    result["skipped"].append(f"custom_{question_id}")
            except Exception as e:
                result["failed"].append(f"custom_{question_id}")
                result["errors"].append(f"Failed to fill custom question {question_id}: {str(e)}")

        return result

    def _map_field_type(self, html_type: str) -> FieldType:
        """Map HTML input type to FieldType."""
        type_mapping = {
            "text": FieldType.TEXT,
            "email": FieldType.EMAIL,
            "tel": FieldType.PHONE,
            "textarea": FieldType.TEXTAREA,
            "select": FieldType.SELECT,
            "select-one": FieldType.SELECT,
            "radio": FieldType.RADIO,
            "checkbox": FieldType.CHECKBOX,
            "file": FieldType.FILE,
            "date": FieldType.DATE,
            "url": FieldType.URL,
            "number": FieldType.NUMBER,
            "hidden": FieldType.HIDDEN,
        }
        return type_mapping.get(html_type.lower(), FieldType.TEXT)

    async def save_progress(self) -> bool:
        """Save current application progress in Workday."""
        try:
            if self._page:
                save_button = await self._page.query_selector(self.SELECTORS["save"])
                if save_button and await save_button.is_visible():
                    await save_button.click()
                    await self._page.wait_for_load_state("networkidle", timeout=10000)
                    return True
        except Exception:
            pass
        return False

    def get_page_state(self) -> WorkdayPageState:
        """Get current page state."""
        return self._page_state
