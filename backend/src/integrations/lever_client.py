"""Lever Postings API client for fetching public job listings.

This module provides async API client for fetching jobs from Lever public postings.
No authentication is required for public postings.

API Documentation:
    - Postings API: https://github.com/lever/postings-api
    - Base URL: https://api.lever.co/v0/postings/{company}

Example usage:
    async with LeverClient() as client:
        # Fetch jobs from a company's postings
        jobs = await client.get_postings("company-name")

        # Get detailed posting information
        posting = await client.get_posting("company-name", "posting_id")

        # Fetch postings with filters
        engineering_jobs = await client.get_postings(
            "company-name",
            team="Engineering",
            location="San Francisco"
        )
"""

import asyncio
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models
# =============================================================================


class LeverCategories(BaseModel):
    """Categories for a Lever posting."""

    commitment: str | None = Field(None, description="Employment type (Full-time, Part-time, etc.)")
    department: str | None = Field(None, description="Department name")
    location: str | None = Field(None, description="Job location")
    team: str | None = Field(None, description="Team name")
    level: str | None = Field(None, description="Seniority level")


class LeverListItem(BaseModel):
    """List item within a posting (for requirements, benefits, etc.)."""

    text: str = Field(..., description="List item content")


class LeverContentBlock(BaseModel):
    """Content block with a heading and list of items."""

    text: str = Field(..., description="Section heading")
    content: str = Field("", description="HTML content")


class LeverPosting(BaseModel):
    """Represents a job posting from Lever Postings API."""

    id: str = Field(..., description="Lever posting ID")
    text: str = Field(..., description="Job title")
    categories: LeverCategories = Field(
        default_factory=LeverCategories, description="Job categories"
    )
    description: str = Field("", description="Job description HTML")
    descriptionPlain: str = Field("", description="Job description plain text")
    lists: list[LeverContentBlock] = Field(
        default_factory=list, description="Structured content lists (requirements, etc.)"
    )
    additional: str = Field("", description="Additional information HTML")
    additionalPlain: str = Field("", description="Additional information plain text")
    hostedUrl: str = Field(..., description="Hosted job posting URL")
    applyUrl: str = Field(..., description="Direct application URL")
    createdAt: int = Field(..., description="Creation timestamp (milliseconds)")
    updatedAt: int | None = Field(None, description="Last update timestamp (milliseconds)")

    # Additional fields that may be present
    workplaceType: str | None = Field(None, description="Workplace type (remote, hybrid, on-site)")
    salaryDescription: str | None = Field(None, description="Salary information")
    salaryDescriptionHtml: str | None = Field(None, description="Salary information HTML")
    salaryRange: dict[str, Any] | None = Field(None, description="Structured salary range")

    # Fields populated by the client
    company: str | None = Field(None, description="Company identifier")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="When fetched")

    @property
    def created_datetime(self) -> datetime:
        """Get creation timestamp as datetime."""
        return datetime.fromtimestamp(self.createdAt / 1000)

    @property
    def updated_datetime(self) -> datetime | None:
        """Get update timestamp as datetime."""
        if self.updatedAt:
            return datetime.fromtimestamp(self.updatedAt / 1000)
        return None

    @property
    def title(self) -> str:
        """Alias for text field (job title)."""
        return self.text

    @property
    def location(self) -> str | None:
        """Get job location from categories."""
        return self.categories.location

    @property
    def department(self) -> str | None:
        """Get department from categories."""
        return self.categories.department

    @property
    def team(self) -> str | None:
        """Get team from categories."""
        return self.categories.team

    @property
    def commitment(self) -> str | None:
        """Get commitment type from categories."""
        return self.categories.commitment


class LeverPostingListItem(BaseModel):
    """Simplified posting for list responses."""

    id: str = Field(..., description="Lever posting ID")
    text: str = Field(..., description="Job title")
    categories: LeverCategories = Field(default_factory=LeverCategories)
    hostedUrl: str = Field(..., description="Hosted job posting URL")
    applyUrl: str = Field(..., description="Direct application URL")
    createdAt: int = Field(..., description="Creation timestamp (milliseconds)")

    # Fields populated by the client
    company: str | None = Field(None, description="Company identifier")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def created_datetime(self) -> datetime:
        """Get creation timestamp as datetime."""
        return datetime.fromtimestamp(self.createdAt / 1000)

    @property
    def title(self) -> str:
        """Alias for text field."""
        return self.text

    @property
    def location(self) -> str | None:
        """Get location from categories."""
        return self.categories.location


class RateLimitStatus(BaseModel):
    """Rate limiting status for API requests."""

    requests_made: int = Field(0, description="Requests made in current window")
    requests_remaining: int = Field(100, description="Requests remaining")
    window_reset_time: datetime | None = Field(None, description="When rate limit resets")
    is_rate_limited: bool = Field(False, description="Whether currently rate limited")


# =============================================================================
# Response Mode Enum
# =============================================================================


class ResponseMode(str, Enum):
    """Response modes for Lever API."""

    JSON = "json"
    HTML = "html"
    MARKDOWN = "md"


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """Token bucket rate limiter for Lever API requests.

    Lever API has reasonable limits for public endpoints.
    Default: 100 requests per minute with minimum 0.5 second between requests.
    """

    def __init__(
        self,
        max_requests_per_minute: int = 100,
        min_delay_seconds: float = 0.5,
    ):
        """Initialize rate limiter.

        Args:
            max_requests_per_minute: Maximum requests allowed per minute.
            min_delay_seconds: Minimum delay between requests.
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.min_delay = min_delay_seconds
        self._request_timestamps: list[float] = []
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0

    def _clean_old_timestamps(self) -> None:
        """Remove timestamps older than 1 minute."""
        one_minute_ago = time.time() - 60
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > one_minute_ago
        ]

    async def acquire(self) -> float:
        """Acquire permission to make a request.

        Returns:
            The delay (in seconds) that was waited.

        Raises:
            LeverRateLimitError: If rate limit is exceeded.
        """
        async with self._lock:
            self._clean_old_timestamps()

            # Check if we've exceeded the rate limit
            if len(self._request_timestamps) >= self.max_requests_per_minute:
                oldest = min(self._request_timestamps)
                wait_time = oldest + 60 - time.time()
                if wait_time > 0:
                    logger.warning(f"Rate limit approaching. Waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
                    self._clean_old_timestamps()

            # Ensure minimum delay between requests
            now = time.time()
            time_since_last = now - self._last_request_time
            if time_since_last < self.min_delay:
                delay = self.min_delay - time_since_last
                await asyncio.sleep(delay)
            else:
                delay = 0

            # Record this request
            self._last_request_time = time.time()
            self._request_timestamps.append(self._last_request_time)

            return delay

    def get_status(self) -> RateLimitStatus:
        """Get current rate limit status."""
        self._clean_old_timestamps()
        requests_made = len(self._request_timestamps)
        requests_remaining = max(0, self.max_requests_per_minute - requests_made)

        window_reset = None
        if self._request_timestamps:
            oldest = min(self._request_timestamps)
            window_reset = datetime.fromtimestamp(oldest + 60)

        return RateLimitStatus(
            requests_made=requests_made,
            requests_remaining=requests_remaining,
            window_reset_time=window_reset,
            is_rate_limited=requests_remaining == 0,
        )


# =============================================================================
# Exceptions
# =============================================================================


class LeverClientError(Exception):
    """Base exception for Lever client errors."""

    pass


class LeverNotFoundError(LeverClientError):
    """Raised when a company or posting is not found."""

    pass


class LeverRateLimitError(LeverClientError):
    """Raised when rate limit is exceeded."""

    pass


class LeverAPIError(LeverClientError):
    """Raised when API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


# =============================================================================
# Lever Client
# =============================================================================


class LeverClient:
    """Async client for Lever Postings API.

    This client fetches public job postings from Lever company pages.
    No authentication is required for public postings.

    Example:
        async with LeverClient() as client:
            # Get all postings from a company
            postings = await client.get_postings("mycompany")

            # Get posting details
            posting = await client.get_posting("mycompany", "abc123")

            # Get postings with filters
            jobs = await client.get_postings(
                "mycompany",
                team="Engineering",
                commitment="Full-time"
            )
    """

    BASE_URL = "https://api.lever.co/v0/postings"

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        timeout: float = 30.0,
    ):
        """Initialize Lever client.

        Args:
            rate_limiter: Optional custom rate limiter.
            timeout: Request timeout in seconds.
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "LeverClient":
        """Async context manager entry."""
        await self._init_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _init_client(self) -> None:
        """Initialize HTTP client."""
        if self._client is not None:
            return

        self._client = httpx.AsyncClient(
            headers={
                "Accept": "application/json",
                "User-Agent": "ResumeCrafter/1.0 (Job Board Integration)",
            },
            timeout=self.timeout,
            follow_redirects=True,
        )

        logger.info("Lever client initialized")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            await self._init_client()
        return self._client  # type: ignore

    async def close(self) -> None:
        """Close HTTP client and release resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("Lever client closed")

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a rate-limited API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            LeverRateLimitError: If rate limit is exceeded
            LeverNotFoundError: If resource not found
            LeverAPIError: If API returns an error
        """
        # Apply rate limiting
        delay = await self.rate_limiter.acquire()
        if delay > 0:
            logger.debug(f"Rate limiter applied {delay:.2f}s delay")

        client = await self._get_client()

        try:
            response = await client.request(method, url, **kwargs)

            if response.status_code == 404:
                raise LeverNotFoundError(f"Resource not found: {url}")
            if response.status_code == 429:
                raise LeverRateLimitError(
                    "Lever API rate limit exceeded. Please wait before making more requests."
                )
            if response.status_code >= 400:
                raise LeverAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {url}")
            raise LeverAPIError(f"Request failed: {e}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise LeverAPIError(f"Request failed: {e}")

    # =========================================================================
    # Postings API Methods
    # =========================================================================

    async def get_postings(
        self,
        company: str,
        skip: int = 0,
        limit: int | None = None,
        mode: ResponseMode = ResponseMode.JSON,
        # Filter parameters
        team: str | None = None,
        department: str | None = None,
        location: str | None = None,
        commitment: str | None = None,
        level: str | None = None,
        group: str | None = None,
    ) -> list[LeverPostingListItem]:
        """Get all postings from a company.

        Args:
            company: The company identifier (from their Lever URL).
            skip: Number of postings to skip (for pagination).
            limit: Maximum number of postings to return (None = all).
            mode: Response mode (json, html, md).
            team: Filter by team name.
            department: Filter by department name.
            location: Filter by location.
            commitment: Filter by commitment type (Full-time, Part-time, etc.).
            level: Filter by seniority level.
            group: Group results by a category field.

        Returns:
            List of job postings.

        Raises:
            LeverNotFoundError: If company doesn't exist.
        """
        logger.info(f"Fetching postings from company: {company}")

        url = f"{self.BASE_URL}/{company}"
        params: dict[str, Any] = {"mode": mode.value}

        if skip > 0:
            params["skip"] = skip
        if limit is not None:
            params["limit"] = limit
        if team:
            params["team"] = team
        if department:
            params["department"] = department
        if location:
            params["location"] = location
        if commitment:
            params["commitment"] = commitment
        if level:
            params["level"] = level
        if group:
            params["group"] = group

        response = await self._make_request("GET", url, params=params)
        data = response.json()

        # Handle both array response and object with nested array
        postings_data = data if isinstance(data, list) else data.get("postings", data)

        postings = []
        for posting_data in postings_data:
            try:
                categories = LeverCategories(
                    commitment=posting_data.get("categories", {}).get("commitment"),
                    department=posting_data.get("categories", {}).get("department"),
                    location=posting_data.get("categories", {}).get("location"),
                    team=posting_data.get("categories", {}).get("team"),
                    level=posting_data.get("categories", {}).get("level"),
                )

                posting = LeverPostingListItem(
                    id=posting_data["id"],
                    text=posting_data["text"],
                    categories=categories,
                    hostedUrl=posting_data["hostedUrl"],
                    applyUrl=posting_data["applyUrl"],
                    createdAt=posting_data["createdAt"],
                    company=company,
                )
                postings.append(posting)
            except Exception as e:
                logger.warning(f"Failed to parse posting: {e}")
                continue

        logger.info(f"Found {len(postings)} postings from company {company}")
        return postings

    async def get_all_postings(
        self,
        company: str,
        batch_size: int = 100,
        **filters: Any,
    ) -> list[LeverPostingListItem]:
        """Get all postings from a company with automatic pagination.

        Args:
            company: The company identifier.
            batch_size: Number of postings to fetch per request.
            **filters: Filter parameters (team, department, location, etc.).

        Returns:
            Complete list of all postings.
        """
        all_postings = []
        skip = 0

        while True:
            postings = await self.get_postings(
                company,
                skip=skip,
                limit=batch_size,
                **filters,
            )

            if not postings:
                break

            all_postings.extend(postings)
            skip += len(postings)

            # If we got fewer than batch_size, we've reached the end
            if len(postings) < batch_size:
                break

        return all_postings

    async def get_posting(
        self,
        company: str,
        posting_id: str,
    ) -> LeverPosting:
        """Get detailed information for a specific posting.

        Args:
            company: The company identifier.
            posting_id: The posting ID.

        Returns:
            Detailed posting information.

        Raises:
            LeverNotFoundError: If posting doesn't exist.
        """
        logger.info(f"Fetching posting {posting_id} from company: {company}")

        url = f"{self.BASE_URL}/{company}/{posting_id}"
        response = await self._make_request("GET", url)
        data = response.json()

        # Parse categories
        categories = LeverCategories(
            commitment=data.get("categories", {}).get("commitment"),
            department=data.get("categories", {}).get("department"),
            location=data.get("categories", {}).get("location"),
            team=data.get("categories", {}).get("team"),
            level=data.get("categories", {}).get("level"),
        )

        # Parse lists (requirements, benefits, etc.)
        lists = []
        for list_item in data.get("lists", []):
            lists.append(LeverContentBlock(
                text=list_item.get("text", ""),
                content=list_item.get("content", ""),
            ))

        return LeverPosting(
            id=data["id"],
            text=data["text"],
            categories=categories,
            description=data.get("description", ""),
            descriptionPlain=data.get("descriptionPlain", ""),
            lists=lists,
            additional=data.get("additional", ""),
            additionalPlain=data.get("additionalPlain", ""),
            hostedUrl=data["hostedUrl"],
            applyUrl=data["applyUrl"],
            createdAt=data["createdAt"],
            updatedAt=data.get("updatedAt"),
            workplaceType=data.get("workplaceType"),
            salaryDescription=data.get("salaryDescription"),
            salaryDescriptionHtml=data.get("salaryDescriptionHtml"),
            salaryRange=data.get("salaryRange"),
            company=company,
        )

    async def get_postings_grouped(
        self,
        company: str,
        group_by: str = "team",
    ) -> dict[str, list[LeverPostingListItem]]:
        """Get postings grouped by a category field.

        Args:
            company: The company identifier.
            group_by: Field to group by (team, department, location, commitment).

        Returns:
            Dictionary with group names as keys and posting lists as values.
        """
        logger.info(f"Fetching postings from {company} grouped by {group_by}")

        url = f"{self.BASE_URL}/{company}"
        params = {"group": group_by}

        response = await self._make_request("GET", url, params=params)
        data = response.json()

        grouped: dict[str, list[LeverPostingListItem]] = {}

        for group in data:
            group_title = group.get("title", "Other")
            postings = []

            for posting_data in group.get("postings", []):
                try:
                    categories = LeverCategories(
                        commitment=posting_data.get("categories", {}).get("commitment"),
                        department=posting_data.get("categories", {}).get("department"),
                        location=posting_data.get("categories", {}).get("location"),
                        team=posting_data.get("categories", {}).get("team"),
                        level=posting_data.get("categories", {}).get("level"),
                    )

                    posting = LeverPostingListItem(
                        id=posting_data["id"],
                        text=posting_data["text"],
                        categories=categories,
                        hostedUrl=posting_data["hostedUrl"],
                        applyUrl=posting_data["applyUrl"],
                        createdAt=posting_data["createdAt"],
                        company=company,
                    )
                    postings.append(posting)
                except Exception as e:
                    logger.warning(f"Failed to parse posting: {e}")
                    continue

            grouped[group_title] = postings

        return grouped

    async def get_postings_from_companies(
        self,
        companies: list[str],
        concurrent_limit: int = 5,
        **filters: Any,
    ) -> list[LeverPostingListItem]:
        """Fetch postings from multiple companies concurrently.

        Args:
            companies: List of company identifiers.
            concurrent_limit: Maximum concurrent requests.
            **filters: Filter parameters to apply to all companies.

        Returns:
            Combined list of postings from all companies.
        """
        logger.info(f"Fetching postings from {len(companies)} companies")

        semaphore = asyncio.Semaphore(concurrent_limit)

        async def fetch_company_postings(company: str) -> list[LeverPostingListItem]:
            async with semaphore:
                try:
                    return await self.get_all_postings(company, **filters)
                except LeverNotFoundError:
                    logger.warning(f"Company not found: {company}")
                    return []
                except Exception as e:
                    logger.error(f"Error fetching company {company}: {e}")
                    return []

        tasks = [fetch_company_postings(company) for company in companies]
        results = await asyncio.gather(*tasks)

        all_postings = []
        for postings in results:
            all_postings.extend(postings)

        logger.info(f"Fetched {len(all_postings)} total postings from {len(companies)} companies")
        return all_postings

    async def search_postings(
        self,
        company: str,
        query: str,
        search_description: bool = True,
    ) -> list[LeverPostingListItem]:
        """Search postings by keyword.

        Note: Lever's public API doesn't have native search, so this
        fetches all postings and filters client-side.

        Args:
            company: The company identifier.
            query: Search query (matches title and optionally description).
            search_description: Whether to also search in description.

        Returns:
            Filtered list of postings.
        """
        postings = await self.get_all_postings(company)
        query_lower = query.lower()

        matching = []
        for posting in postings:
            if query_lower in posting.text.lower():
                matching.append(posting)
            elif search_description:
                # Need to fetch full posting to search description
                try:
                    full_posting = await self.get_posting(company, posting.id)
                    if query_lower in full_posting.descriptionPlain.lower():
                        matching.append(posting)
                except Exception:
                    continue

        return matching

    def get_rate_limit_status(self) -> RateLimitStatus:
        """Get current rate limit status.

        Returns:
            RateLimitStatus with current usage information.
        """
        return self.rate_limiter.get_status()


# =============================================================================
# Convenience Functions
# =============================================================================


async def fetch_lever_postings(
    company: str,
    team: str | None = None,
    location: str | None = None,
    commitment: str | None = None,
) -> list[LeverPostingListItem]:
    """Convenience function to fetch postings from a Lever company.

    Args:
        company: The company identifier.
        team: Optional team filter.
        location: Optional location filter.
        commitment: Optional commitment filter (Full-time, Part-time, etc.).

    Returns:
        List of job postings.

    Example:
        jobs = await fetch_lever_postings("mycompany")
        for job in jobs:
            print(f"{job.title} - {job.location}")
    """
    async with LeverClient() as client:
        return await client.get_all_postings(
            company,
            team=team,
            location=location,
            commitment=commitment,
        )


async def fetch_lever_posting_details(
    company: str,
    posting_id: str,
) -> LeverPosting:
    """Convenience function to fetch detailed posting information.

    Args:
        company: The company identifier.
        posting_id: The posting ID.

    Returns:
        Detailed posting information.

    Example:
        posting = await fetch_lever_posting_details("mycompany", "abc123")
        print(f"{posting.title}: {posting.description}")
    """
    async with LeverClient() as client:
        return await client.get_posting(company, posting_id)


async def fetch_postings_from_multiple_companies(
    companies: list[str],
    **filters: Any,
) -> list[LeverPostingListItem]:
    """Convenience function to fetch postings from multiple companies.

    Args:
        companies: List of company identifiers.
        **filters: Filter parameters (team, location, commitment, etc.).

    Returns:
        Combined list of postings from all companies.

    Example:
        jobs = await fetch_postings_from_multiple_companies(
            ["company1", "company2"],
            commitment="Full-time"
        )
    """
    async with LeverClient() as client:
        return await client.get_postings_from_companies(companies, **filters)
