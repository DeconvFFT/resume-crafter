"""Greenhouse ATS form handler."""

import re
from typing import Any

from .base import (
    ATSPlatform,
    BaseATSHandler,
    FieldType,
    FormDetectionResult,
    FormField,
    FormFieldMapping,
    FormFillingResult,
)


class GreenhouseHandler(BaseATSHandler):
    """Handler for Greenhouse ATS forms (boards.greenhouse.io)."""

    platform = ATSPlatform.GREENHOUSE

    # URL patterns for Greenhouse
    URL_PATTERNS = [
        r"boards\.greenhouse\.io",
        r"job-boards\.greenhouse\.io",
        r"\.greenhouse\.io/embed/job_app",
    ]

    # Common CSS selectors for Greenhouse forms
    SELECTORS = {
        "form": "#application-form, form[data-job-application]",
        "first_name": "#first_name, input[name='first_name']",
        "last_name": "#last_name, input[name='last_name']",
        "email": "#email, input[name='email'], input[type='email']",
        "phone": "#phone, input[name='phone'], input[type='tel']",
        "resume": "#resume, input[name='resume'], input[data-field='resume']",
        "cover_letter": "#cover_letter, input[name='cover_letter'], textarea[name='cover_letter']",
        "linkedin": "#job_application_answers_attributes_0_text_value, input[name*='linkedin']",
        "submit": "button[type='submit'], input[type='submit'], #submit_app",
        "custom_question": ".field, .application-field",
    }

    # Field label patterns for auto-detection
    FIELD_PATTERNS = {
        "first_name": [r"first\s*name", r"given\s*name"],
        "last_name": [r"last\s*name", r"surname", r"family\s*name"],
        "email": [r"email", r"e-mail"],
        "phone": [r"phone", r"telephone", r"mobile", r"cell"],
        "resume": [r"resume", r"cv", r"curriculum\s*vitae"],
        "cover_letter": [r"cover\s*letter", r"covering\s*letter"],
        "linkedin": [r"linkedin", r"linked\s*in"],
        "website": [r"website", r"portfolio", r"personal\s*site"],
        "github": [r"github", r"git\s*hub"],
        "location": [r"location", r"address", r"city"],
        "salary": [r"salary", r"compensation", r"pay"],
        "start_date": [r"start\s*date", r"availability", r"when\s*can\s*you"],
        "work_authorization": [r"work\s*authorization", r"visa", r"eligible\s*to\s*work", r"sponsorship"],
    }

    async def detect_platform(self, url: str, html: str | None = None) -> FormDetectionResult:
        """Detect if URL belongs to Greenhouse."""
        url_matched = any(re.search(pattern, url, re.IGNORECASE) for pattern in self.URL_PATTERNS)
        dom_matched = False
        confidence = 0.0
        metadata = {}

        if url_matched:
            confidence = 0.8

        if html:
            # Check for Greenhouse-specific DOM elements
            greenhouse_indicators = [
                "greenhouse.io",
                "data-greenhouse",
                "grnhse",
                "greenhouse-job-board",
                "application_form",
            ]
            for indicator in greenhouse_indicators:
                if indicator.lower() in html.lower():
                    dom_matched = True
                    confidence = min(confidence + 0.1, 1.0)

            # Extract job ID if present
            job_id_match = re.search(r"job[_-]?id[=:]?\s*['\"]?(\d+)", html, re.IGNORECASE)
            if job_id_match:
                metadata["job_id"] = job_id_match.group(1)

        return FormDetectionResult(
            platform=self.platform,
            confidence=confidence,
            url_pattern_matched=url_matched,
            dom_pattern_matched=dom_matched,
            metadata=metadata,
        )

    async def get_form_fields(self, url: str) -> list[FormField]:
        """Extract form fields from Greenhouse application page."""
        fields = []

        try:
            page = await self._get_page(url)

            # Wait for form to load
            await page.wait_for_selector(self.SELECTORS["form"], timeout=10000)

            # Extract all input fields
            field_data = await page.evaluate(
                """
                () => {
                    const fields = [];
                    const form = document.querySelector('#application-form, form[data-job-application], form');
                    if (!form) return fields;

                    // Get all inputs, textareas, and selects
                    const inputs = form.querySelectorAll('input, textarea, select');

                    inputs.forEach(input => {
                        if (input.type === 'hidden' && !input.name.includes('authenticity')) return;

                        const field = {
                            name: input.name || input.id || '',
                            type: input.type || input.tagName.toLowerCase(),
                            id: input.id || '',
                            required: input.required || input.getAttribute('aria-required') === 'true',
                            placeholder: input.placeholder || '',
                            value: input.value || '',
                            options: [],
                            accepts: input.accept || '',
                        };

                        // Get label
                        let label = '';
                        const labelEl = document.querySelector(`label[for="${input.id}"]`);
                        if (labelEl) {
                            label = labelEl.textContent.trim();
                        } else {
                            // Check parent for label
                            const parent = input.closest('.field, .form-group, .application-field');
                            if (parent) {
                                const parentLabel = parent.querySelector('label');
                                if (parentLabel) label = parentLabel.textContent.trim();
                            }
                        }
                        field.label = label;

                        // Get select options
                        if (input.tagName === 'SELECT') {
                            const options = input.querySelectorAll('option');
                            field.options = Array.from(options).map(opt => ({
                                value: opt.value,
                                text: opt.textContent.trim()
                            }));
                        }

                        // Build selector
                        if (input.id) {
                            field.selector = '#' + input.id;
                        } else if (input.name) {
                            field.selector = `[name="${input.name}"]`;
                        }

                        fields.push(field);
                    });

                    return fields;
                }
            """
            )

            for data in field_data:
                field_type = self._map_field_type(data.get("type", "text"))
                options = None
                if data.get("options"):
                    options = [opt["text"] for opt in data["options"] if opt["value"]]

                accepts = None
                if data.get("accepts"):
                    accepts = [a.strip() for a in data["accepts"].split(",")]

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
                        accepts=accepts,
                    )
                )

        except Exception as e:
            # Return empty list with error logging
            pass

        return fields

    async def fill_form(
        self,
        url: str,
        field_mapping: FormFieldMapping,
        submit: bool = False,
    ) -> FormFillingResult:
        """Fill out Greenhouse application form."""
        filled = []
        failed = []
        skipped = []
        errors = []

        try:
            page = await self._get_page(url)
            await page.wait_for_selector(self.SELECTORS["form"], timeout=10000)

            # Map standard fields
            field_mappings = [
                (self.SELECTORS["first_name"], field_mapping.first_name, "first_name"),
                (self.SELECTORS["last_name"], field_mapping.last_name, "last_name"),
                (self.SELECTORS["email"], field_mapping.email, "email"),
                (self.SELECTORS["phone"], field_mapping.phone, "phone"),
                (self.SELECTORS["linkedin"], field_mapping.linkedin_url, "linkedin"),
            ]

            # Fill full name if first/last not available
            if field_mapping.full_name and not (field_mapping.first_name and field_mapping.last_name):
                # Try to find a single name field
                name_selector = "input[name*='name']:not([name*='first']):not([name*='last'])"
                if await page.query_selector(name_selector):
                    field_mappings.append((name_selector, field_mapping.full_name, "full_name"))

            # Fill text fields
            for selector, value, field_name in field_mappings:
                if not value:
                    skipped.append(field_name)
                    continue

                try:
                    element = await page.query_selector(selector)
                    if element:
                        await element.fill(value)
                        filled.append(field_name)
                    else:
                        skipped.append(field_name)
                except Exception as e:
                    failed.append(field_name)
                    errors.append(f"Failed to fill {field_name}: {str(e)}")

            # Handle resume upload
            if field_mapping.resume_path:
                try:
                    resume_input = await page.query_selector(self.SELECTORS["resume"])
                    if resume_input:
                        await resume_input.set_input_files(field_mapping.resume_path)
                        filled.append("resume")
                    else:
                        skipped.append("resume")
                except Exception as e:
                    failed.append("resume")
                    errors.append(f"Failed to upload resume: {str(e)}")

            # Handle cover letter
            if field_mapping.cover_letter_path or field_mapping.cover_letter_text:
                try:
                    cover_letter_input = await page.query_selector(self.SELECTORS["cover_letter"])
                    if cover_letter_input:
                        tag_name = await cover_letter_input.evaluate("el => el.tagName.toLowerCase()")
                        if tag_name == "textarea" and field_mapping.cover_letter_text:
                            await cover_letter_input.fill(field_mapping.cover_letter_text)
                            filled.append("cover_letter")
                        elif tag_name == "input" and field_mapping.cover_letter_path:
                            await cover_letter_input.set_input_files(field_mapping.cover_letter_path)
                            filled.append("cover_letter")
                        else:
                            skipped.append("cover_letter")
                    else:
                        skipped.append("cover_letter")
                except Exception as e:
                    failed.append("cover_letter")
                    errors.append(f"Failed to fill cover letter: {str(e)}")

            # Handle custom questions
            for question_id, answer in field_mapping.custom_answers.items():
                try:
                    # Try different selector patterns for custom questions
                    selectors_to_try = [
                        f"#{question_id}",
                        f"[name='{question_id}']",
                        f"[data-question-id='{question_id}']",
                    ]
                    filled_custom = False
                    for sel in selectors_to_try:
                        element = await page.query_selector(sel)
                        if element:
                            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
                            if tag_name == "select":
                                await element.select_option(str(answer))
                            elif tag_name in ("input", "textarea"):
                                await element.fill(str(answer))
                            filled.append(f"custom_{question_id}")
                            filled_custom = True
                            break
                    if not filled_custom:
                        skipped.append(f"custom_{question_id}")
                except Exception as e:
                    failed.append(f"custom_{question_id}")
                    errors.append(f"Failed to fill custom question {question_id}: {str(e)}")

            # Submit if requested
            next_step_url = None
            if submit:
                try:
                    submit_button = await page.query_selector(self.SELECTORS["submit"])
                    if submit_button:
                        await submit_button.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        next_step_url = page.url
                except Exception as e:
                    errors.append(f"Failed to submit form: {str(e)}")

            return FormFillingResult(
                success=len(failed) == 0,
                fields_filled=filled,
                fields_failed=failed,
                fields_skipped=skipped,
                errors=errors,
                next_step_url=next_step_url,
                requires_manual_intervention=len(failed) > 0,
                intervention_reason="Some fields could not be filled automatically" if failed else None,
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

    def _map_field_type(self, html_type: str) -> FieldType:
        """Map HTML input type to FieldType."""
        type_mapping = {
            "text": FieldType.TEXT,
            "email": FieldType.EMAIL,
            "tel": FieldType.PHONE,
            "textarea": FieldType.TEXTAREA,
            "select": FieldType.SELECT,
            "radio": FieldType.RADIO,
            "checkbox": FieldType.CHECKBOX,
            "file": FieldType.FILE,
            "date": FieldType.DATE,
            "url": FieldType.URL,
            "number": FieldType.NUMBER,
            "hidden": FieldType.HIDDEN,
        }
        return type_mapping.get(html_type.lower(), FieldType.TEXT)

    def _identify_field_purpose(self, label: str, name: str) -> str | None:
        """Identify the purpose of a field based on its label and name."""
        combined = f"{label} {name}".lower()

        for purpose, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined, re.IGNORECASE):
                    return purpose

        return None
