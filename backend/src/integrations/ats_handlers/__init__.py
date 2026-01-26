"""ATS form handlers for automated job application filling.

This module provides handlers for various Applicant Tracking Systems (ATS)
including Greenhouse, Lever, and Workday. Each handler can detect its platform,
extract form fields, and fill applications using Playwright browser automation.

Example usage:
    from integrations.ats_handlers import get_handler, detect_platform, ATSPlatform

    # Auto-detect platform and get handler
    handler = await get_handler(url)
    if handler:
        fields = await handler.get_form_fields(url)
        result = await handler.fill_form(url, field_mapping)
        await handler.close()

    # Or detect platform first
    platform, detection = await detect_platform(url)
    if platform:
        handler = create_handler(platform)
        ...
"""

from .base import (
    ATSPlatform,
    BaseATSHandler,
    FieldType,
    FormDetectionResult,
    FormField,
    FormFieldMapping,
    FormFillingResult,
)
from .greenhouse import GreenhouseHandler
from .lever import LeverHandler
from .workday import WorkdayAuthConfig, WorkdayHandler, WorkdayPageState

__all__ = [
    # Enums and models
    "ATSPlatform",
    "FieldType",
    "FormField",
    "FormFieldMapping",
    "FormDetectionResult",
    "FormFillingResult",
    # Base class
    "BaseATSHandler",
    # Handlers
    "GreenhouseHandler",
    "LeverHandler",
    "WorkdayHandler",
    # Workday-specific models
    "WorkdayAuthConfig",
    "WorkdayPageState",
    # Factory functions
    "create_handler",
    "detect_platform",
    "get_handler",
]


def create_handler(
    platform: ATSPlatform,
    workday_auth: WorkdayAuthConfig | None = None,
) -> BaseATSHandler:
    """Create a handler instance for the specified ATS platform.

    Args:
        platform: The ATS platform type.
        workday_auth: Optional authentication config for Workday.

    Returns:
        An instance of the appropriate handler.

    Raises:
        ValueError: If the platform is not supported.
    """
    handlers = {
        ATSPlatform.GREENHOUSE: GreenhouseHandler,
        ATSPlatform.LEVER: LeverHandler,
        ATSPlatform.WORKDAY: lambda: WorkdayHandler(auth_config=workday_auth),
    }

    if platform == ATSPlatform.CUSTOM:
        raise ValueError(
            "Custom platform requires a specific handler implementation. "
            "Consider creating a subclass of BaseATSHandler."
        )

    handler_factory = handlers.get(platform)
    if not handler_factory:
        raise ValueError(f"Unsupported ATS platform: {platform}")

    if platform == ATSPlatform.WORKDAY:
        return handler_factory()
    return handler_factory()


async def detect_platform(
    url: str,
    html: str | None = None,
) -> tuple[ATSPlatform | None, FormDetectionResult | None]:
    """Detect which ATS platform a URL belongs to.

    Checks all supported platforms and returns the one with highest confidence.

    Args:
        url: The job application URL to check.
        html: Optional HTML content for more accurate detection.

    Returns:
        Tuple of (platform, detection_result) or (None, None) if not detected.
    """
    handlers = [
        GreenhouseHandler(),
        LeverHandler(),
        WorkdayHandler(),
    ]

    best_platform: ATSPlatform | None = None
    best_result: FormDetectionResult | None = None
    best_confidence = 0.0

    try:
        for handler in handlers:
            result = await handler.detect_platform(url, html)
            if result.confidence > best_confidence:
                best_confidence = result.confidence
                best_platform = handler.platform
                best_result = result
    finally:
        # Clean up handlers
        for handler in handlers:
            await handler.close()

    # Only return if confidence is above threshold
    if best_confidence >= 0.5:
        return best_platform, best_result

    return None, None


async def get_handler(
    url: str,
    html: str | None = None,
    workday_auth: WorkdayAuthConfig | None = None,
) -> BaseATSHandler | None:
    """Get the appropriate handler for a job application URL.

    Auto-detects the platform and returns a handler instance.

    Args:
        url: The job application URL.
        html: Optional HTML content for better detection.
        workday_auth: Optional Workday authentication config.

    Returns:
        Handler instance or None if platform not detected.
    """
    platform, _ = await detect_platform(url, html)

    if platform:
        return create_handler(platform, workday_auth=workday_auth)

    return None
