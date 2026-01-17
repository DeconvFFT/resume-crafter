"""Validation tools for agent use.

Provides tools for validating URLs, dates, and other data.
"""

import logging
import re
from datetime import date, datetime
from urllib.parse import urlparse

import httpx

from .registry import ToolRegistry, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


def register_validation_tools(registry: ToolRegistry) -> None:
    """Register validation tools with the registry."""

    @registry.register(
        name="validate_url",
        description="Validate that a URL is accessible and determine its type",
        parameters=[
            ToolParameter(
                name="url",
                type="string",
                description="The URL to validate",
            ),
            ToolParameter(
                name="expected_type",
                type="string",
                description="Expected URL type (github, demo, docs, video, paper, other)",
                required=False,
                enum=["github", "demo", "docs", "video", "paper", "other"],
            ),
        ],
    )
    async def validate_url(url: str, expected_type: str | None = None) -> ToolResult:
        """Validate URL accessibility and type."""
        # Basic URL validation
        if not url or not url.strip():
            return ToolResult(
                status=ToolStatus.ERROR,
                error="URL is empty",
            )

        url = url.strip()

        # Check URL format
        if not url.startswith(("http://", "https://")):
            return ToolResult(
                status=ToolStatus.ERROR,
                error="URL must start with http:// or https://",
            )

        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error="Invalid URL format",
                )
        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Invalid URL: {e}",
            )

        # Reject localhost/internal URLs
        invalid_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
        if any(h in parsed.netloc.lower() for h in invalid_hosts):
            return ToolResult(
                status=ToolStatus.ERROR,
                error="Local/internal URLs are not allowed",
            )

        # Detect URL type
        detected_type = _detect_url_type(url)

        # Check expected type if provided
        if expected_type and detected_type != expected_type:
            logger.debug(f"URL type mismatch: expected {expected_type}, detected {detected_type}")

        # Try to access the URL (with timeout)
        is_accessible = await _check_url_accessible(url)

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "url": url,
                "is_valid": True,
                "is_accessible": is_accessible,
                "detected_type": detected_type,
                "expected_type": expected_type,
                "type_matches": expected_type is None or detected_type == expected_type,
            },
        )

    @registry.register(
        name="validate_date_range",
        description="Validate that a date range is logical (start before end, reasonable dates)",
        parameters=[
            ToolParameter(
                name="start_date",
                type="string",
                description="Start date in YYYY-MM or YYYY-MM-DD format",
            ),
            ToolParameter(
                name="end_date",
                type="string",
                description="End date in YYYY-MM or YYYY-MM-DD format (optional for current)",
                required=False,
            ),
            ToolParameter(
                name="is_current",
                type="boolean",
                description="Whether this is a current/ongoing position",
                required=False,
            ),
        ],
    )
    async def validate_date_range(
        start_date: str,
        end_date: str | None = None,
        is_current: bool = False,
    ) -> ToolResult:
        """Validate date range logic."""
        issues = []

        # Parse start date
        start = _parse_date(start_date)
        if not start:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"Invalid start date format: {start_date}",
            )

        # Check start date is reasonable (not too far in past or future)
        today = date.today()
        min_reasonable_date = date(1950, 1, 1)
        max_future_date = date(today.year + 2, 12, 31)

        if start < min_reasonable_date:
            issues.append(f"Start date {start_date} seems too far in the past")
        if start > max_future_date:
            issues.append(f"Start date {start_date} is too far in the future")

        # Parse and validate end date
        end = None
        if end_date and not is_current:
            end = _parse_date(end_date)
            if not end:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Invalid end date format: {end_date}",
                )

            if end < start:
                issues.append("End date is before start date")
            if end > max_future_date:
                issues.append(f"End date {end_date} is too far in the future")

        # If current, check start isn't in the future
        if is_current and start > today:
            issues.append("Current position cannot start in the future")

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "start_date": start_date,
                "end_date": end_date,
                "is_current": is_current,
                "is_valid": len(issues) == 0,
                "issues": issues,
                "parsed_start": start.isoformat() if start else None,
                "parsed_end": end.isoformat() if end else None,
            },
        )


def _detect_url_type(url: str) -> str:
    """Detect the type of URL based on domain and path."""
    url_lower = url.lower()

    if "github.com" in url_lower or "gitlab.com" in url_lower or "bitbucket.org" in url_lower:
        return "github"
    if "youtube.com" in url_lower or "youtu.be" in url_lower or "vimeo.com" in url_lower:
        return "video"
    if "arxiv.org" in url_lower or "doi.org" in url_lower or "researchgate" in url_lower:
        return "paper"
    if "/docs" in url_lower or "/documentation" in url_lower or "readthedocs" in url_lower:
        return "docs"
    if "heroku" in url_lower or "vercel" in url_lower or "netlify" in url_lower:
        return "demo"

    return "other"


async def _check_url_accessible(url: str, timeout: float = 5.0) -> bool:
    """Check if a URL is accessible via HEAD request."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.head(url)
            return response.status_code < 400
    except Exception:
        # Try GET as fallback (some servers don't support HEAD)
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url, headers={"Range": "bytes=0-0"})
                return response.status_code < 400
        except Exception:
            return False


def _parse_date(date_str: str | None) -> date | None:
    """Parse a date string in various formats."""
    if not date_str:
        return None

    date_str = date_str.strip()

    # Try various formats
    formats = [
        "%Y-%m-%d",
        "%Y-%m",
        "%Y/%m/%d",
        "%Y/%m",
        "%m/%d/%Y",
        "%m/%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()
        except ValueError:
            continue

    # Try just year
    if re.match(r"^\d{4}$", date_str):
        try:
            return date(int(date_str), 1, 1)
        except ValueError:
            pass

    return None
