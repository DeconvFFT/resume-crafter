"""Lever ATS form handler."""

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


class LeverHandler(BaseATSHandler):
    """Handler for Lever ATS forms (jobs.lever.co)."""

    platform = ATSPlatform.LEVER

    # URL patterns for Lever
    URL_PATTERNS = [
        r"jobs\.lever\.co",
        r"lever\.co/.*?/apply",
        r"\.lever\.co/",
    ]

    # CSS selectors for Lever forms
    SELECTORS = {
        "form": "form.application-form, form[action*='apply'], .application-page form",
        "name": "input[name='name'], input[name='full_name'], #name",
        "email": "input[name='email'], input[type='email'], #email",
        "phone": "input[name='phone'], input[type='tel'], #phone",
        "resume": "input[name='resume'], input[type='file'][accept*='pdf'], .resume-upload input",
        "cover_letter": "textarea[name='comments'], textarea[name='cover_letter'], #comments",
        "linkedin": "input[name*='linkedin'], input[data-field='urls[LinkedIn]']",
        "website": "input[name*='website'], input[name*='portfolio']",
        "github": "input[name*='github']",
        "current_company": "input[name*='company'], input[name*='org']",
        "submit": "button[type='submit'], input[type='submit'], .btn-submit",
        "next_step": ".btn-next, button[data-action='next'], .next-step",
        "custom_question": ".custom-question, .additional-field, [data-custom-field]",
    }

    # Multi-step form indicators
    STEP_INDICATORS = [
        ".step-indicator",
        ".progress-bar",
        "[data-step]",
        ".form-step",
    ]

    async def detect_platform(self, url: str, html: str | None = None) -> FormDetectionResult:
        """Detect if URL belongs to Lever."""
        url_matched = any(re.search(pattern, url, re.IGNORECASE) for pattern in self.URL_PATTERNS)
        dom_matched = False
        confidence = 0.0
        metadata = {}

        if url_matched:
            confidence = 0.85

        if html:
            # Check for Lever-specific DOM elements
            lever_indicators = [
                "lever.co",
                "lever-job",
                "posting-page",
                "posting-headline",
                "application-form",
                "lever-application",
            ]
            for indicator in lever_indicators:
                if indicator.lower() in html.lower():
                    dom_matched = True
                    confidence = min(confidence + 0.1, 1.0)

            # Extract job/posting ID if present
            posting_id_match = re.search(r"posting[_-]?id[=:]\s*['\"]?([a-f0-9-]+)", html, re.IGNORECASE)
            if posting_id_match:
                metadata["posting_id"] = posting_id_match.group(1)

            # Check for multi-step form
            for indicator in self.STEP_INDICATORS:
                if indicator in html:
                    metadata["is_multi_step"] = True
                    break

        return FormDetectionResult(
            platform=self.platform,
            confidence=confidence,
            url_pattern_matched=url_matched,
            dom_pattern_matched=dom_matched,
            metadata=metadata,
        )

    async def get_form_fields(self, url: str) -> list[FormField]:
        """Extract form fields from Lever application page."""
        fields = []

        try:
            page = await self._get_page(url)

            # Wait for form to load
            await page.wait_for_selector(self.SELECTORS["form"], timeout=10000)

            # Check if we need to click "Apply" first
            apply_button = await page.query_selector(
                "a[href*='apply'], button[data-action='apply'], .btn-apply"
            )
            if apply_button:
                await apply_button.click()
                await page.wait_for_load_state("networkidle", timeout=10000)

            # Collect fields from all steps if multi-step form
            all_fields_data = []
            step_count = 1

            while True:
                # Extract fields from current step
                step_fields = await self._extract_step_fields(page)
                all_fields_data.extend(step_fields)

                # Check for next step button
                next_button = await page.query_selector(self.SELECTORS["next_step"])
                if next_button and await next_button.is_visible():
                    # Check if we can proceed (some steps require filling before next)
                    is_enabled = await next_button.is_enabled()
                    if is_enabled and step_count < 5:  # Max 5 steps safety limit
                        await next_button.click()
                        await page.wait_for_load_state("networkidle", timeout=5000)
                        step_count += 1
                        continue
                break

            # Convert to FormField objects
            for data in all_fields_data:
                field_type = self._map_field_type(data.get("type", "text"))
                options = None
                if data.get("options"):
                    options = [opt["text"] for opt in data["options"] if opt.get("value")]

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
            # Log error and return empty list
            pass

        return fields

    async def _extract_step_fields(self, page) -> list[dict[str, Any]]:
        """Extract form fields from current form step."""
        return await page.evaluate(
            """
            () => {
                const fields = [];
                const form = document.querySelector('form.application-form, form[action*="apply"], form');
                if (!form) return fields;

                const inputs = form.querySelectorAll('input:not([type="hidden"]), textarea, select');

                inputs.forEach(input => {
                    // Skip hidden and submit buttons
                    if (input.type === 'submit' || input.type === 'button') return;

                    const field = {
                        name: input.name || input.id || '',
                        type: input.type || input.tagName.toLowerCase(),
                        id: input.id || '',
                        required: input.required || input.getAttribute('aria-required') === 'true',
                        placeholder: input.placeholder || '',
                        value: input.value || '',
                        options: [],
                    };

                    // Get label
                    let label = '';
                    const labelEl = document.querySelector(`label[for="${input.id}"]`);
                    if (labelEl) {
                        label = labelEl.textContent.trim();
                    } else {
                        // Check parent containers for label
                        const parent = input.closest('.form-group, .field-container, .application-field');
                        if (parent) {
                            const parentLabel = parent.querySelector('label, .label, .field-label');
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

                    // Handle radio buttons
                    if (input.type === 'radio') {
                        const radioGroup = form.querySelectorAll(`input[name="${input.name}"]`);
                        const existingField = fields.find(f => f.name === input.name);
                        if (!existingField) {
                            field.options = Array.from(radioGroup).map(radio => ({
                                value: radio.value,
                                text: document.querySelector(`label[for="${radio.id}"]`)?.textContent?.trim() || radio.value
                            }));
                        } else {
                            return; // Skip duplicate radio entries
                        }
                    }

                    // Build selector
                    if (input.id) {
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
        """Fill out Lever application form, handling multi-step flows."""
        filled = []
        failed = []
        skipped = []
        errors = []

        try:
            page = await self._get_page(url)
            await page.wait_for_selector(self.SELECTORS["form"], timeout=10000)

            # Click Apply button if present
            apply_button = await page.query_selector(
                "a[href*='apply'], button[data-action='apply'], .btn-apply"
            )
            if apply_button and await apply_button.is_visible():
                await apply_button.click()
                await page.wait_for_load_state("networkidle", timeout=10000)

            # Handle multi-step forms
            max_steps = 5
            current_step = 0

            while current_step < max_steps:
                current_step += 1

                # Fill fields on current step
                step_result = await self._fill_step_fields(page, field_mapping)
                filled.extend(step_result["filled"])
                failed.extend(step_result["failed"])
                skipped.extend(step_result["skipped"])
                errors.extend(step_result["errors"])

                # Check for next step
                next_button = await page.query_selector(self.SELECTORS["next_step"])
                if next_button and await next_button.is_visible() and await next_button.is_enabled():
                    await next_button.click()
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    # Check if we're still on an application form
                    form = await page.query_selector(self.SELECTORS["form"])
                    if not form:
                        break
                else:
                    break

            # Submit if requested
            next_step_url = None
            if submit:
                try:
                    submit_button = await page.query_selector(self.SELECTORS["submit"])
                    if submit_button and await submit_button.is_visible():
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

    async def _fill_step_fields(
        self, page, field_mapping: FormFieldMapping
    ) -> dict[str, list[str]]:
        """Fill fields on the current form step."""
        result = {"filled": [], "failed": [], "skipped": [], "errors": []}

        # Standard field mappings for Lever
        field_selectors = [
            (self.SELECTORS["name"], field_mapping.full_name or f"{field_mapping.first_name or ''} {field_mapping.last_name or ''}".strip(), "name"),
            (self.SELECTORS["email"], field_mapping.email, "email"),
            (self.SELECTORS["phone"], field_mapping.phone, "phone"),
            (self.SELECTORS["linkedin"], field_mapping.linkedin_url, "linkedin"),
            (self.SELECTORS["website"], field_mapping.portfolio_url, "website"),
            (self.SELECTORS["github"], field_mapping.github_url, "github"),
            (self.SELECTORS["current_company"], field_mapping.current_company, "current_company"),
        ]

        # Fill text fields
        for selector, value, field_name in field_selectors:
            if not value:
                result["skipped"].append(field_name)
                continue

            try:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
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
                    # Try drag-drop or button click upload
                    upload_button = await page.query_selector(
                        ".resume-upload button, [data-action='upload-resume'], .upload-btn"
                    )
                    if upload_button:
                        # Trigger file chooser
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

        # Handle cover letter (Lever often uses "comments" field)
        if field_mapping.cover_letter_text:
            try:
                cover_input = await page.query_selector(self.SELECTORS["cover_letter"])
                if cover_input and await cover_input.is_visible():
                    await cover_input.fill(field_mapping.cover_letter_text)
                    result["filled"].append("cover_letter")
                else:
                    result["skipped"].append("cover_letter")
            except Exception as e:
                result["failed"].append("cover_letter")
                result["errors"].append(f"Failed to fill cover letter: {str(e)}")

        # Handle custom questions
        for question_id, answer in field_mapping.custom_answers.items():
            try:
                selectors_to_try = [
                    f"#{question_id}",
                    f"[name='{question_id}']",
                    f"[data-field='{question_id}']",
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
                            # Find and click the matching radio option
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
