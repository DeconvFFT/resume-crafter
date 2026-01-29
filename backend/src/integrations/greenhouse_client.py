"""Greenhouse Job Board API client for fetching public job listings.

This module provides async API client for fetching jobs from Greenhouse public job boards.
No authentication is required for public boards.

API Documentation:
    - Job Board API: https://developers.greenhouse.io/job-board.html
    - Base URL: https://boards-api.greenhouse.io/v1/boards/{board_token}/

Example usage:
    async with GreenhouseClient() as client:
        # Fetch jobs from a company's board
        jobs = await client.get_jobs("company_board_token")

        # Get detailed job information
        job = await client.get_job("company_board_token", "job_id")

        # Fetch jobs from multiple boards
        all_jobs = await client.get_jobs_from_boards(["token1", "token2"])
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


class GreenhouseLocation(BaseModel):
    """Location information for a Greenhouse job posting."""

    name: str = Field(..., description="Location name")


class GreenhouseDepartment(BaseModel):
    """Department information for a Greenhouse job posting."""

    id: int = Field(..., description="Department ID")
    name: str = Field(..., description="Department name")
    parent_id: int | None = Field(None, description="Parent department ID")
    child_ids: list[int] = Field(default_factory=list, description="Child department IDs")


class GreenhouseOffice(BaseModel):
    """Office information for a Greenhouse job posting."""

    id: int = Field(..., description="Office ID")
    name: str = Field(..., description="Office name")
    location: str | None = Field(None, description="Office location")
    parent_id: int | None = Field(None, description="Parent office ID")
    child_ids: list[int] = Field(default_factory=list, description="Child office IDs")


class GreenhouseMetadata(BaseModel):
    """Metadata field for a Greenhouse job posting."""

    id: int = Field(..., description="Metadata field ID")
    name: str = Field(..., description="Metadata field name")
    value_type: str = Field(..., description="Type of the value")
    value: Any = Field(None, description="Metadata value")


class GreenhouseJob(BaseModel):
    """Represents a job posting from Greenhouse Job Board API."""

    id: int = Field(..., description="Greenhouse job ID")
    title: str = Field(..., description="Job title")
    location: GreenhouseLocation = Field(..., description="Job location")
    content: str = Field("", description="Job description HTML content")
    departments: list[GreenhouseDepartment] = Field(
        default_factory=list, description="Associated departments"
    )
    offices: list[GreenhouseOffice] = Field(
        default_factory=list, description="Associated offices"
    )
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    absolute_url: str = Field(..., description="Direct URL to job posting")
    internal_job_id: int | None = Field(None, description="Internal job ID")
    metadata: list[GreenhouseMetadata] = Field(
        default_factory=list, description="Custom metadata fields"
    )
    requisition_id: str | None = Field(None, description="Requisition ID")
    data_compliance: list[dict[str, Any]] = Field(
        default_factory=list, description="Data compliance information"
    )

    # Fields populated by the client
    board_token: str | None = Field(None, description="Board token this job was fetched from")
    fetched_at: datetime = Field(default_factory=datetime.utcnow, description="When the job was fetched")

    @field_validator("updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime | None:
        """Parse datetime from various formats."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Greenhouse uses ISO 8601 format
            try:
                # Handle format: "2024-01-15T10:30:00-05:00"
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Failed to parse datetime: {v}")
                return None
        return None


class GreenhouseJobListItem(BaseModel):
    """Simplified job listing item (from list endpoint)."""

    id: int = Field(..., description="Greenhouse job ID")
    title: str = Field(..., description="Job title")
    location: GreenhouseLocation = Field(..., description="Job location")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    absolute_url: str = Field(..., description="Direct URL to job posting")
    internal_job_id: int | None = Field(None, description="Internal job ID")
    requisition_id: str | None = Field(None, description="Requisition ID")

    # Fields populated by the client
    board_token: str | None = Field(None, description="Board token")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("updated_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime | None:
        """Parse datetime from various formats."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None


class GreenhouseBoardInfo(BaseModel):
    """Information about a Greenhouse job board."""

    name: str = Field(..., description="Company/board name")
    content: str | None = Field(None, description="Board description")


class GreenhouseJobsResponse(BaseModel):
    """Response from the jobs list endpoint."""

    jobs: list[GreenhouseJobListItem] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class RateLimitStatus(BaseModel):
    """Rate limiting status for API requests."""

    requests_made: int = Field(0, description="Requests made in current window")
    requests_remaining: int = Field(100, description="Requests remaining")
    window_reset_time: datetime | None = Field(None, description="When rate limit resets")
    is_rate_limited: bool = Field(False, description="Whether currently rate limited")


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """Token bucket rate limiter for Greenhouse API requests.

    Greenhouse API has generous limits for public endpoints, but we implement
    rate limiting to be a good API citizen and avoid potential blocks.

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
            GreenhouseRateLimitError: If rate limit is exceeded.
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


class GreenhouseClientError(Exception):
    """Base exception for Greenhouse client errors."""

    pass


class GreenhouseNotFoundError(GreenhouseClientError):
    """Raised when a board or job is not found."""

    pass


class GreenhouseRateLimitError(GreenhouseClientError):
    """Raised when rate limit is exceeded."""

    pass


class GreenhouseAPIError(GreenhouseClientError):
    """Raised when API returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


# =============================================================================
# Greenhouse Client
# =============================================================================


class GreenhouseClient:
    """Async client for Greenhouse Job Board API.

    This client fetches public job listings from Greenhouse job boards.
    No authentication is required for public boards.

    Example:
        async with GreenhouseClient() as client:
            # Get all jobs from a board
            jobs = await client.get_jobs("mycompany")

            # Get job details
            job = await client.get_job("mycompany", 12345)

            # Get board info
            info = await client.get_board_info("mycompany")
    """

    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(
        self,
        rate_limiter: RateLimiter | None = None,
        timeout: float = 30.0,
    ):
        """Initialize Greenhouse client.

        Args:
            rate_limiter: Optional custom rate limiter.
            timeout: Request timeout in seconds.
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GreenhouseClient":
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

        logger.info("Greenhouse client initialized")

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
        logger.info("Greenhouse client closed")

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
            GreenhouseRateLimitError: If rate limit is exceeded
            GreenhouseNotFoundError: If resource not found
            GreenhouseAPIError: If API returns an error
        """
        # Apply rate limiting
        delay = await self.rate_limiter.acquire()
        if delay > 0:
            logger.debug(f"Rate limiter applied {delay:.2f}s delay")

        client = await self._get_client()

        try:
            response = await client.request(method, url, **kwargs)

            if response.status_code == 404:
                raise GreenhouseNotFoundError(
                    f"Resource not found: {url}"
                )
            if response.status_code == 429:
                raise GreenhouseRateLimitError(
                    "Greenhouse API rate limit exceeded. Please wait before making more requests."
                )
            if response.status_code >= 400:
                raise GreenhouseAPIError(
                    f"API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                )

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {url}")
            raise GreenhouseAPIError(f"Request failed: {e}", status_code=e.response.status_code)
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise GreenhouseAPIError(f"Request failed: {e}")

    # =========================================================================
    # Job Board API Methods
    # =========================================================================

    async def get_board_info(self, board_token: str) -> GreenhouseBoardInfo:
        """Get information about a job board.

        Args:
            board_token: The company's board token (from their Greenhouse URL).

        Returns:
            Board information including name and description.

        Raises:
            GreenhouseNotFoundError: If board doesn't exist.
        """
        logger.info(f"Fetching board info for: {board_token}")

        url = f"{self.BASE_URL}/{board_token}"
        response = await self._make_request("GET", url)
        data = response.json()

        return GreenhouseBoardInfo(
            name=data.get("name", ""),
            content=data.get("content"),
        )

    async def get_jobs(
        self,
        board_token: str,
        content: bool = False,
    ) -> list[GreenhouseJobListItem]:
        """Get all jobs from a board.

        Args:
            board_token: The company's board token.
            content: Whether to include job description content (slower).

        Returns:
            List of job listings.

        Raises:
            GreenhouseNotFoundError: If board doesn't exist.
        """
        logger.info(f"Fetching jobs from board: {board_token}")

        url = f"{self.BASE_URL}/{board_token}/jobs"
        params = {}
        if content:
            params["content"] = "true"

        response = await self._make_request("GET", url, params=params)
        data = response.json()

        jobs = []
        for job_data in data.get("jobs", []):
            try:
                job = GreenhouseJobListItem(
                    id=job_data["id"],
                    title=job_data["title"],
                    location=GreenhouseLocation(**job_data.get("location", {"name": ""})),
                    updated_at=job_data.get("updated_at"),
                    absolute_url=job_data["absolute_url"],
                    internal_job_id=job_data.get("internal_job_id"),
                    requisition_id=job_data.get("requisition_id"),
                    board_token=board_token,
                )
                jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job: {e}")
                continue

        logger.info(f"Found {len(jobs)} jobs from board {board_token}")
        return jobs

    async def get_job(
        self,
        board_token: str,
        job_id: int | str,
        questions: bool = False,
    ) -> GreenhouseJob:
        """Get detailed information for a specific job.

        Args:
            board_token: The company's board token.
            job_id: The job ID.
            questions: Whether to include application questions.

        Returns:
            Detailed job information.

        Raises:
            GreenhouseNotFoundError: If job doesn't exist.
        """
        logger.info(f"Fetching job {job_id} from board: {board_token}")

        url = f"{self.BASE_URL}/{board_token}/jobs/{job_id}"
        params = {}
        if questions:
            params["questions"] = "true"

        response = await self._make_request("GET", url, params=params)
        data = response.json()

        # Parse departments
        departments = []
        for dept in data.get("departments", []):
            departments.append(GreenhouseDepartment(
                id=dept["id"],
                name=dept["name"],
                parent_id=dept.get("parent_id"),
                child_ids=dept.get("child_ids", []),
            ))

        # Parse offices
        offices = []
        for office in data.get("offices", []):
            offices.append(GreenhouseOffice(
                id=office["id"],
                name=office["name"],
                location=office.get("location"),
                parent_id=office.get("parent_id"),
                child_ids=office.get("child_ids", []),
            ))

        # Parse metadata
        metadata = []
        for meta in data.get("metadata", []):
            metadata.append(GreenhouseMetadata(
                id=meta["id"],
                name=meta["name"],
                value_type=meta.get("value_type", "text"),
                value=meta.get("value"),
            ))

        return GreenhouseJob(
            id=data["id"],
            title=data["title"],
            location=GreenhouseLocation(**data.get("location", {"name": ""})),
            content=data.get("content", ""),
            departments=departments,
            offices=offices,
            updated_at=data.get("updated_at"),
            absolute_url=data["absolute_url"],
            internal_job_id=data.get("internal_job_id"),
            metadata=metadata,
            requisition_id=data.get("requisition_id"),
            data_compliance=data.get("data_compliance", []),
            board_token=board_token,
        )

    async def get_departments(self, board_token: str) -> list[GreenhouseDepartment]:
        """Get all departments for a board.

        Args:
            board_token: The company's board token.

        Returns:
            List of departments.
        """
        logger.info(f"Fetching departments for board: {board_token}")

        url = f"{self.BASE_URL}/{board_token}/departments"
        response = await self._make_request("GET", url)
        data = response.json()

        departments = []
        for dept in data.get("departments", []):
            departments.append(GreenhouseDepartment(
                id=dept["id"],
                name=dept["name"],
                parent_id=dept.get("parent_id"),
                child_ids=dept.get("child_ids", []),
            ))

        return departments

    async def get_offices(self, board_token: str) -> list[GreenhouseOffice]:
        """Get all offices for a board.

        Args:
            board_token: The company's board token.

        Returns:
            List of offices.
        """
        logger.info(f"Fetching offices for board: {board_token}")

        url = f"{self.BASE_URL}/{board_token}/offices"
        response = await self._make_request("GET", url)
        data = response.json()

        offices = []
        for office in data.get("offices", []):
            offices.append(GreenhouseOffice(
                id=office["id"],
                name=office["name"],
                location=office.get("location"),
                parent_id=office.get("parent_id"),
                child_ids=office.get("child_ids", []),
            ))

        return offices

    async def get_jobs_from_boards(
        self,
        board_tokens: list[str],
        content: bool = False,
        concurrent_limit: int = 5,
    ) -> list[GreenhouseJobListItem]:
        """Fetch jobs from multiple boards concurrently.

        Args:
            board_tokens: List of board tokens to fetch from.
            content: Whether to include job description content.
            concurrent_limit: Maximum concurrent requests.

        Returns:
            Combined list of jobs from all boards.
        """
        logger.info(f"Fetching jobs from {len(board_tokens)} boards")

        semaphore = asyncio.Semaphore(concurrent_limit)

        async def fetch_board_jobs(token: str) -> list[GreenhouseJobListItem]:
            async with semaphore:
                try:
                    return await self.get_jobs(token, content=content)
                except GreenhouseNotFoundError:
                    logger.warning(f"Board not found: {token}")
                    return []
                except Exception as e:
                    logger.error(f"Error fetching board {token}: {e}")
                    return []

        tasks = [fetch_board_jobs(token) for token in board_tokens]
        results = await asyncio.gather(*tasks)

        all_jobs = []
        for jobs in results:
            all_jobs.extend(jobs)

        logger.info(f"Fetched {len(all_jobs)} total jobs from {len(board_tokens)} boards")
        return all_jobs

    async def search_jobs(
        self,
        board_token: str,
        query: str | None = None,
        department_id: int | None = None,
        office_id: int | None = None,
    ) -> list[GreenhouseJobListItem]:
        """Search jobs on a board with filters.

        Note: Greenhouse's public API doesn't have native search, so this
        filters results client-side.

        Args:
            board_token: The company's board token.
            query: Optional search query (matches title).
            department_id: Optional department ID to filter by.
            office_id: Optional office ID to filter by.

        Returns:
            Filtered list of jobs.
        """
        jobs = await self.get_jobs(board_token)

        if query:
            query_lower = query.lower()
            jobs = [j for j in jobs if query_lower in j.title.lower()]

        if department_id or office_id:
            # Need to fetch full job details for filtering
            filtered_jobs = []
            for job_item in jobs:
                try:
                    job = await self.get_job(board_token, job_item.id)

                    if department_id:
                        dept_ids = [d.id for d in job.departments]
                        if department_id not in dept_ids:
                            continue

                    if office_id:
                        office_ids = [o.id for o in job.offices]
                        if office_id not in office_ids:
                            continue

                    filtered_jobs.append(job_item)
                except Exception as e:
                    logger.warning(f"Error fetching job details: {e}")
                    continue

            jobs = filtered_jobs

        return jobs

    def get_rate_limit_status(self) -> RateLimitStatus:
        """Get current rate limit status.

        Returns:
            RateLimitStatus with current usage information.
        """
        return self.rate_limiter.get_status()


# =============================================================================
# Convenience Functions
# =============================================================================


async def fetch_greenhouse_jobs(
    board_token: str,
    include_content: bool = False,
) -> list[GreenhouseJobListItem]:
    """Convenience function to fetch jobs from a Greenhouse board.

    Args:
        board_token: The company's board token.
        include_content: Whether to include job description content.

    Returns:
        List of job listings.

    Example:
        jobs = await fetch_greenhouse_jobs("mycompany")
        for job in jobs:
            print(f"{job.title} - {job.location.name}")
    """
    async with GreenhouseClient() as client:
        return await client.get_jobs(board_token, content=include_content)


async def fetch_greenhouse_job_details(
    board_token: str,
    job_id: int | str,
) -> GreenhouseJob:
    """Convenience function to fetch detailed job information.

    Args:
        board_token: The company's board token.
        job_id: The job ID.

    Returns:
        Detailed job information.

    Example:
        job = await fetch_greenhouse_job_details("mycompany", 12345)
        print(f"{job.title}: {job.content}")
    """
    async with GreenhouseClient() as client:
        return await client.get_job(board_token, job_id)


async def fetch_jobs_from_multiple_boards(
    board_tokens: list[str],
) -> list[GreenhouseJobListItem]:
    """Convenience function to fetch jobs from multiple boards.

    Args:
        board_tokens: List of board tokens.

    Returns:
        Combined list of jobs from all boards.

    Example:
        jobs = await fetch_jobs_from_multiple_boards(["company1", "company2"])
    """
    async with GreenhouseClient() as client:
        return await client.get_jobs_from_boards(board_tokens)
