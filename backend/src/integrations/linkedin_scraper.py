"""LinkedIn scraper integration for job search and contact discovery.

This module provides async LinkedIn scraping capabilities including:
- Job search with filters (location, experience level, date posted, remote options)
- People search for finding hiring managers and recruiters
- Profile data extraction for contact discovery

IMPORTANT: This is a scaffold implementation. LinkedIn scraping requires
valid session cookies (li_at) provided by the user. The user must be authenticated
to LinkedIn and provide their session cookie for this scraper to work.

LinkedIn's Terms of Service should be reviewed before using this scraper.
"""

import asyncio
import logging
import random
import re
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from urllib.parse import quote_plus, urlencode

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Enums for LinkedIn Search Filters
# =============================================================================


class ExperienceLevel(str, Enum):
    """LinkedIn experience level filters."""

    INTERNSHIP = "1"
    ENTRY_LEVEL = "2"
    ASSOCIATE = "3"
    MID_SENIOR = "4"
    DIRECTOR = "5"
    EXECUTIVE = "6"


class DatePosted(str, Enum):
    """LinkedIn date posted filters."""

    PAST_24_HOURS = "r86400"
    PAST_WEEK = "r604800"
    PAST_MONTH = "r2592000"
    ANY_TIME = ""


class RemoteOption(str, Enum):
    """LinkedIn remote work filters."""

    ON_SITE = "1"
    REMOTE = "2"
    HYBRID = "3"


class JobType(str, Enum):
    """LinkedIn job type filters."""

    FULL_TIME = "F"
    PART_TIME = "P"
    CONTRACT = "C"
    TEMPORARY = "T"
    VOLUNTEER = "V"
    INTERNSHIP = "I"


# =============================================================================
# Pydantic Models
# =============================================================================


class LinkedInSearchConfig(BaseModel):
    """Configuration for LinkedIn job search."""

    keywords: str = Field(..., description="Search keywords")
    location: str | None = Field(None, description="Location filter (city, state, or country)")
    experience_levels: list[ExperienceLevel] = Field(
        default_factory=list, description="Experience level filters"
    )
    date_posted: DatePosted = Field(
        default=DatePosted.ANY_TIME, description="Date posted filter"
    )
    remote_options: list[RemoteOption] = Field(
        default_factory=list, description="Remote work options"
    )
    job_types: list[JobType] = Field(default_factory=list, description="Job type filters")
    company_ids: list[str] = Field(
        default_factory=list, description="LinkedIn company IDs to filter by"
    )
    salary_min: int | None = Field(None, ge=0, description="Minimum salary filter")
    easy_apply_only: bool = Field(False, description="Only show Easy Apply jobs")
    max_results: int = Field(25, ge=1, le=100, description="Maximum results to fetch")


class LinkedInJobResult(BaseModel):
    """Represents a LinkedIn job listing."""

    job_id: str = Field(..., description="LinkedIn job ID")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    company_id: str | None = Field(None, description="LinkedIn company ID")
    company_logo_url: str | None = Field(None, description="Company logo URL")
    location: str | None = Field(None, description="Job location")
    posted_date: str | None = Field(None, description="When the job was posted")
    applicant_count: str | None = Field(None, description="Number of applicants")
    job_url: str = Field(..., description="Direct URL to job posting")
    description_snippet: str | None = Field(None, description="Short description snippet")
    is_remote: bool = Field(False, description="Whether job is remote")
    is_easy_apply: bool = Field(False, description="Whether Easy Apply is available")
    salary_range: str | None = Field(None, description="Salary range if available")
    employment_type: str | None = Field(None, description="Full-time, Part-time, etc.")
    seniority_level: str | None = Field(None, description="Entry level, Mid-Senior, etc.")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("job_url", mode="before")
    @classmethod
    def ensure_full_url(cls, v: str) -> str:
        """Ensure job URL is a full URL."""
        if v and not v.startswith("http"):
            return f"https://www.linkedin.com{v}"
        return v


class LinkedInProfileResult(BaseModel):
    """Represents a LinkedIn profile from people search."""

    profile_id: str = Field(..., description="LinkedIn profile ID or public identifier")
    full_name: str = Field(..., description="Person's full name")
    headline: str | None = Field(None, description="Profile headline")
    location: str | None = Field(None, description="Person's location")
    profile_url: str = Field(..., description="URL to profile")
    profile_picture_url: str | None = Field(None, description="Profile picture URL")
    current_company: str | None = Field(None, description="Current company name")
    current_title: str | None = Field(None, description="Current job title")
    connection_degree: str | None = Field(None, description="Connection degree (1st, 2nd, 3rd)")
    shared_connections: int | None = Field(None, description="Number of shared connections")
    is_premium: bool = Field(False, description="Whether profile has Premium badge")
    is_open_to_work: bool = Field(False, description="Whether showing Open to Work badge")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("profile_url", mode="before")
    @classmethod
    def ensure_full_url(cls, v: str) -> str:
        """Ensure profile URL is a full URL."""
        if v and not v.startswith("http"):
            return f"https://www.linkedin.com{v}"
        return v


class LinkedInCompanyInfo(BaseModel):
    """Basic company information from LinkedIn."""

    company_id: str = Field(..., description="LinkedIn company ID")
    name: str = Field(..., description="Company name")
    industry: str | None = Field(None, description="Company industry")
    company_size: str | None = Field(None, description="Company size range")
    headquarters: str | None = Field(None, description="Headquarters location")
    company_url: str = Field(..., description="LinkedIn company page URL")
    logo_url: str | None = Field(None, description="Company logo URL")


class RateLimitStatus(BaseModel):
    """Rate limiting status."""

    requests_made: int = Field(0, description="Requests made in current window")
    requests_remaining: int = Field(30, description="Requests remaining in current window")
    window_reset_time: datetime | None = Field(None, description="When the rate limit window resets")
    is_rate_limited: bool = Field(False, description="Whether currently rate limited")


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """Token bucket rate limiter for LinkedIn requests.

    Implements a sliding window rate limiter with:
    - Maximum 30 requests per hour
    - Random delays between 5-15 seconds between requests
    """

    def __init__(
        self,
        max_requests_per_hour: int = 30,
        min_delay_seconds: float = 5.0,
        max_delay_seconds: float = 15.0,
    ):
        """Initialize rate limiter.

        Args:
            max_requests_per_hour: Maximum requests allowed per hour.
            min_delay_seconds: Minimum delay between requests.
            max_delay_seconds: Maximum delay between requests.
        """
        self.max_requests_per_hour = max_requests_per_hour
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds
        self._request_timestamps: list[float] = []
        self._lock = asyncio.Lock()

    def _clean_old_timestamps(self) -> None:
        """Remove timestamps older than 1 hour."""
        one_hour_ago = time.time() - 3600
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > one_hour_ago
        ]

    async def acquire(self) -> float:
        """Acquire permission to make a request.

        Returns:
            The delay (in seconds) that was waited.

        Raises:
            RateLimitExceeded: If rate limit is exceeded and cannot wait.
        """
        async with self._lock:
            self._clean_old_timestamps()

            # Check if we've exceeded the rate limit
            if len(self._request_timestamps) >= self.max_requests_per_hour:
                oldest = min(self._request_timestamps)
                wait_time = oldest + 3600 - time.time()
                if wait_time > 0:
                    logger.warning(
                        f"Rate limit reached. Need to wait {wait_time:.1f}s"
                    )
                    raise RateLimitExceeded(
                        f"Rate limit exceeded. Try again in {wait_time:.1f} seconds."
                    )

            # Add random delay for anti-detection
            delay = random.uniform(self.min_delay, self.max_delay)
            await asyncio.sleep(delay)

            # Record this request
            self._request_timestamps.append(time.time())

            return delay

    def get_status(self) -> RateLimitStatus:
        """Get current rate limit status."""
        self._clean_old_timestamps()
        requests_made = len(self._request_timestamps)
        requests_remaining = max(0, self.max_requests_per_hour - requests_made)

        window_reset = None
        if self._request_timestamps:
            oldest = min(self._request_timestamps)
            window_reset = datetime.fromtimestamp(oldest + 3600)

        return RateLimitStatus(
            requests_made=requests_made,
            requests_remaining=requests_remaining,
            window_reset_time=window_reset,
            is_rate_limited=requests_remaining == 0,
        )


# =============================================================================
# Exceptions
# =============================================================================


class LinkedInScraperError(Exception):
    """Base exception for LinkedIn scraper."""

    pass


class AuthenticationError(LinkedInScraperError):
    """Raised when authentication fails or session is invalid."""

    pass


class RateLimitExceeded(LinkedInScraperError):
    """Raised when rate limit is exceeded."""

    pass


class ScrapingError(LinkedInScraperError):
    """Raised when scraping fails."""

    pass


# =============================================================================
# User Agent Rotation
# =============================================================================


class UserAgentRotator:
    """Rotates through realistic user agents for anti-detection."""

    USER_AGENTS = [
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    def __init__(self):
        """Initialize user agent rotator."""
        self._current_index = random.randint(0, len(self.USER_AGENTS) - 1)

    def get_random(self) -> str:
        """Get a random user agent."""
        return random.choice(self.USER_AGENTS)

    def get_next(self) -> str:
        """Get the next user agent in rotation."""
        self._current_index = (self._current_index + 1) % len(self.USER_AGENTS)
        return self.USER_AGENTS[self._current_index]


# =============================================================================
# LinkedIn Scraper
# =============================================================================


class LinkedInScraper:
    """Async LinkedIn scraper with rate limiting and anti-detection.

    This scraper provides functionality for:
    - Job search with comprehensive filters
    - People search for finding contacts at companies
    - Profile data extraction

    IMPORTANT: Requires valid LinkedIn session cookies (li_at) to function.
    The user must provide their own session cookie after logging into LinkedIn.

    Example usage:
        async with LinkedInScraper(session_cookie="your_li_at_cookie") as scraper:
            jobs = await scraper.search_jobs(
                LinkedInSearchConfig(
                    keywords="Software Engineer",
                    location="San Francisco",
                    experience_levels=[ExperienceLevel.MID_SENIOR],
                    date_posted=DatePosted.PAST_WEEK,
                )
            )
    """

    BASE_URL = "https://www.linkedin.com"
    JOBS_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOBS_API_URL = "https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards"
    PEOPLE_SEARCH_URL = "https://www.linkedin.com/voyager/api/graphql"

    def __init__(
        self,
        session_cookie: str | None = None,
        csrf_token: str | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        """Initialize LinkedIn scraper.

        Args:
            session_cookie: LinkedIn session cookie (li_at value).
                           Required for authenticated requests.
            csrf_token: CSRF token (JSESSIONID). If not provided, will attempt
                       to extract from session.
            rate_limiter: Optional custom rate limiter. Defaults to 30 req/hour.
        """
        self.session_cookie = session_cookie
        self.csrf_token = csrf_token
        self.rate_limiter = rate_limiter or RateLimiter()
        self.user_agent_rotator = UserAgentRotator()
        self._client: httpx.AsyncClient | None = None
        self._authenticated = False

    async def __aenter__(self) -> "LinkedInScraper":
        """Async context manager entry."""
        await self._init_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _init_client(self) -> None:
        """Initialize HTTP client with appropriate headers."""
        if self._client is not None:
            return

        headers = self._build_headers()

        cookies = {}
        if self.session_cookie:
            cookies["li_at"] = self.session_cookie
            self._authenticated = True
        if self.csrf_token:
            cookies["JSESSIONID"] = f'"{self.csrf_token}"'

        self._client = httpx.AsyncClient(
            headers=headers,
            cookies=cookies,
            follow_redirects=True,
            timeout=30.0,
        )

        logger.info(
            f"LinkedIn scraper initialized. Authenticated: {self._authenticated}"
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with anti-detection measures."""
        headers = {
            "User-Agent": self.user_agent_rotator.get_random(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        # Add CSRF token for API requests if available
        if self.csrf_token:
            headers["csrf-token"] = self.csrf_token

        return headers

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
        logger.info("LinkedIn scraper closed")

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make a rate-limited request with anti-detection measures.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            RateLimitExceeded: If rate limit is exceeded
            AuthenticationError: If session is invalid
            ScrapingError: If request fails
        """
        # Apply rate limiting
        delay = await self.rate_limiter.acquire()
        logger.debug(f"Rate limiter applied {delay:.1f}s delay")

        # Rotate user agent occasionally
        client = await self._get_client()
        if random.random() < 0.3:  # 30% chance to rotate
            client.headers["User-Agent"] = self.user_agent_rotator.get_next()

        try:
            response = await client.request(method, url, **kwargs)

            # Check for authentication issues
            if response.status_code == 401:
                raise AuthenticationError(
                    "Session cookie is invalid or expired. Please provide a fresh li_at cookie."
                )
            if response.status_code == 403:
                raise AuthenticationError(
                    "Access forbidden. LinkedIn may have detected automated access."
                )
            if response.status_code == 429:
                raise RateLimitExceeded(
                    "LinkedIn rate limit hit. Please wait before making more requests."
                )

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {url}")
            raise ScrapingError(f"Request failed: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ScrapingError(f"Request failed: {e}")

    # =========================================================================
    # Job Search
    # =========================================================================

    def _build_job_search_params(
        self,
        config: LinkedInSearchConfig,
        start: int = 0,
    ) -> dict[str, str]:
        """Build query parameters for job search.

        Args:
            config: Search configuration
            start: Pagination start offset

        Returns:
            Dictionary of query parameters
        """
        params: dict[str, str] = {
            "keywords": config.keywords,
            "start": str(start),
        }

        if config.location:
            params["location"] = config.location

        # Experience levels (f_E parameter)
        if config.experience_levels:
            params["f_E"] = ",".join(level.value for level in config.experience_levels)

        # Date posted (f_TPR parameter)
        if config.date_posted and config.date_posted != DatePosted.ANY_TIME:
            params["f_TPR"] = config.date_posted.value

        # Remote options (f_WT parameter)
        if config.remote_options:
            params["f_WT"] = ",".join(option.value for option in config.remote_options)

        # Job types (f_JT parameter)
        if config.job_types:
            params["f_JT"] = ",".join(jt.value for jt in config.job_types)

        # Company IDs (f_C parameter)
        if config.company_ids:
            params["f_C"] = ",".join(config.company_ids)

        # Salary filter (f_SB2 parameter - salary bucket)
        if config.salary_min:
            # LinkedIn uses salary buckets, map to appropriate one
            salary_bucket = self._get_salary_bucket(config.salary_min)
            if salary_bucket:
                params["f_SB2"] = salary_bucket

        # Easy Apply filter
        if config.easy_apply_only:
            params["f_AL"] = "true"

        return params

    def _get_salary_bucket(self, min_salary: int) -> str | None:
        """Map minimum salary to LinkedIn salary bucket.

        LinkedIn uses salary buckets for filtering:
        1 = $40,000+
        2 = $60,000+
        3 = $80,000+
        4 = $100,000+
        5 = $120,000+
        6 = $140,000+
        7 = $160,000+
        8 = $180,000+
        9 = $200,000+
        """
        buckets = [
            (200000, "9"),
            (180000, "8"),
            (160000, "7"),
            (140000, "6"),
            (120000, "5"),
            (100000, "4"),
            (80000, "3"),
            (60000, "2"),
            (40000, "1"),
        ]

        for threshold, bucket in buckets:
            if min_salary >= threshold:
                return bucket

        return None

    async def search_jobs(
        self,
        config: LinkedInSearchConfig,
    ) -> list[LinkedInJobResult]:
        """Search for jobs on LinkedIn.

        Args:
            config: Search configuration with keywords, filters, etc.

        Returns:
            List of job results matching the search criteria.

        Raises:
            AuthenticationError: If session is invalid
            RateLimitExceeded: If rate limit is exceeded
            ScrapingError: If scraping fails
        """
        logger.info(f"Searching jobs: {config.keywords} in {config.location}")

        jobs: list[LinkedInJobResult] = []
        start = 0
        page_size = 25

        while len(jobs) < config.max_results:
            params = self._build_job_search_params(config, start)

            # Use guest API for unauthenticated or the Voyager API for authenticated
            if self._authenticated:
                job_results = await self._search_jobs_authenticated(params)
            else:
                job_results = await self._search_jobs_guest(params)

            if not job_results:
                break

            jobs.extend(job_results)
            start += page_size

            # Add extra random delay between pagination requests
            if len(jobs) < config.max_results:
                await asyncio.sleep(random.uniform(2.0, 5.0))

        # Trim to max_results
        jobs = jobs[: config.max_results]

        logger.info(f"Found {len(jobs)} jobs")
        return jobs

    async def _search_jobs_guest(
        self,
        params: dict[str, str],
    ) -> list[LinkedInJobResult]:
        """Search jobs using the guest (unauthenticated) API.

        This endpoint works without authentication but may have limited results.
        """
        url = f"{self.JOBS_SEARCH_URL}?{urlencode(params)}"

        response = await self._make_request("GET", url)
        html = response.text

        return self._parse_job_cards_html(html)

    async def _search_jobs_authenticated(
        self,
        params: dict[str, str],
    ) -> list[LinkedInJobResult]:
        """Search jobs using the authenticated Voyager API.

        Requires valid session cookie. Provides richer results.
        """
        # For authenticated requests, use the Voyager API format
        # This requires CSRF token and proper headers
        url = f"{self.BASE_URL}/jobs/search?{urlencode(params)}"

        response = await self._make_request("GET", url)
        html = response.text

        return self._parse_job_cards_html(html)

    def _parse_job_cards_html(self, html: str) -> list[LinkedInJobResult]:
        """Parse job cards from HTML response.

        Args:
            html: Raw HTML from LinkedIn

        Returns:
            List of parsed job results
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[LinkedInJobResult] = []

        # Find job cards - LinkedIn uses different classes
        job_cards = soup.select(
            "div.job-search-card, "
            "li.jobs-search-results__list-item, "
            "div.base-card"
        )

        for card in job_cards:
            try:
                job = self._parse_single_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job card: {e}")
                continue

        return jobs

    def _parse_single_job_card(self, card: BeautifulSoup) -> LinkedInJobResult | None:
        """Parse a single job card element.

        Args:
            card: BeautifulSoup element for the job card

        Returns:
            Parsed job result or None if parsing fails
        """
        # Extract job ID from data attributes or link
        job_id = None
        job_link = card.select_one("a.base-card__full-link, a.job-card-list__title")
        if job_link:
            href = job_link.get("href", "")
            # Extract job ID from URL like /jobs/view/1234567890/
            match = re.search(r"/jobs/view/(\d+)", href)
            if match:
                job_id = match.group(1)
            job_url = href
        else:
            return None

        if not job_id:
            # Try data attribute
            job_id = card.get("data-job-id", card.get("data-entity-urn", ""))
            if "urn:li:jobPosting:" in job_id:
                job_id = job_id.split(":")[-1]

        if not job_id:
            return None

        # Extract title
        title_el = card.select_one(
            "h3.base-search-card__title, "
            "a.job-card-list__title, "
            "span.sr-only"
        )
        title = title_el.get_text(strip=True) if title_el else "Unknown Title"

        # Extract company
        company_el = card.select_one(
            "h4.base-search-card__subtitle a, "
            "a.job-card-container__company-name, "
            "span.job-card-container__primary-description"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown Company"

        # Extract company ID from link
        company_id = None
        if company_el and company_el.name == "a":
            company_href = company_el.get("href", "")
            match = re.search(r"/company/([^/\?]+)", company_href)
            if match:
                company_id = match.group(1)

        # Extract location
        location_el = card.select_one(
            "span.job-search-card__location, "
            "li.job-card-container__metadata-item"
        )
        location = location_el.get_text(strip=True) if location_el else None

        # Extract posted date
        posted_el = card.select_one("time, span.job-search-card__listdate")
        posted_date = None
        if posted_el:
            posted_date = posted_el.get("datetime") or posted_el.get_text(strip=True)

        # Extract company logo
        logo_el = card.select_one("img.artdeco-entity-image, img.job-card-container__company-logo")
        company_logo_url = logo_el.get("data-delayed-url") or logo_el.get("src") if logo_el else None

        # Check for Easy Apply badge
        easy_apply = bool(
            card.select_one(
                "span.job-card-container__apply-method, "
                "li.job-card-container__footer-item--highlighted"
            )
        )

        # Check for remote badge
        is_remote = "remote" in (location or "").lower()

        # Extract description snippet if available
        desc_el = card.select_one("p.job-search-card__snippet")
        description_snippet = desc_el.get_text(strip=True) if desc_el else None

        return LinkedInJobResult(
            job_id=job_id,
            title=title,
            company=company,
            company_id=company_id,
            company_logo_url=company_logo_url,
            location=location,
            posted_date=posted_date,
            job_url=job_url,
            description_snippet=description_snippet,
            is_remote=is_remote,
            is_easy_apply=easy_apply,
        )

    async def get_job_details(self, job_id: str) -> dict[str, Any]:
        """Fetch detailed information for a specific job.

        Args:
            job_id: LinkedIn job ID

        Returns:
            Dictionary with full job details including description
        """
        url = f"{self.BASE_URL}/jobs/view/{job_id}"

        response = await self._make_request("GET", url)
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        # Extract detailed information
        details: dict[str, Any] = {"job_id": job_id, "url": url}

        # Title
        title_el = soup.select_one(
            "h1.top-card-layout__title, "
            "h1.job-details-jobs-unified-top-card__job-title"
        )
        details["title"] = title_el.get_text(strip=True) if title_el else None

        # Company
        company_el = soup.select_one(
            "a.topcard__org-name-link, "
            "a.job-details-jobs-unified-top-card__company-name"
        )
        details["company"] = company_el.get_text(strip=True) if company_el else None

        # Location
        location_el = soup.select_one(
            "span.topcard__flavor--bullet, "
            "span.job-details-jobs-unified-top-card__bullet"
        )
        details["location"] = location_el.get_text(strip=True) if location_el else None

        # Description
        desc_el = soup.select_one(
            "div.description__text, "
            "div.jobs-description__content, "
            "div.show-more-less-html__markup"
        )
        if desc_el:
            # Clean up the description
            for element in desc_el(["script", "style"]):
                element.decompose()
            details["description"] = desc_el.get_text(separator="\n", strip=True)
            details["description_html"] = str(desc_el)

        # Seniority level
        seniority_el = soup.select_one(
            "span.description__job-criteria-text:has(span.description__job-criteria-subheader:contains('Seniority'))"
        )
        details["seniority_level"] = (
            seniority_el.get_text(strip=True) if seniority_el else None
        )

        # Employment type
        emp_type_el = soup.select_one(
            "span.description__job-criteria-text:has(span.description__job-criteria-subheader:contains('Employment'))"
        )
        details["employment_type"] = (
            emp_type_el.get_text(strip=True) if emp_type_el else None
        )

        # Applicant count
        applicants_el = soup.select_one(
            "span.num-applicants__caption, "
            "span.jobs-unified-top-card__bullet"
        )
        if applicants_el:
            text = applicants_el.get_text(strip=True)
            if "applicant" in text.lower():
                details["applicant_count"] = text

        return details

    # =========================================================================
    # People Search
    # =========================================================================

    async def search_people(
        self,
        keywords: str,
        company: str | None = None,
        title: str | None = None,
        location: str | None = None,
        max_results: int = 10,
    ) -> list[LinkedInProfileResult]:
        """Search for people on LinkedIn.

        Useful for finding hiring managers, recruiters, and contacts at companies.

        Args:
            keywords: Search keywords (name, skills, etc.)
            company: Filter by current company
            title: Filter by current title (e.g., "Recruiter", "Hiring Manager")
            location: Filter by location
            max_results: Maximum number of results to return

        Returns:
            List of profile results

        Raises:
            AuthenticationError: Session required for people search
        """
        if not self._authenticated:
            raise AuthenticationError(
                "People search requires authentication. Please provide a valid li_at cookie."
            )

        logger.info(f"Searching people: {keywords}, company={company}, title={title}")

        # Build search URL
        search_params = {"keywords": keywords}
        if company:
            search_params["company"] = company
        if title:
            search_params["title"] = title
        if location:
            search_params["geoUrn"] = location

        url = f"{self.BASE_URL}/search/results/people/?{urlencode(search_params)}"

        response = await self._make_request("GET", url)
        html = response.text

        profiles = self._parse_people_search_html(html)

        return profiles[:max_results]

    def _parse_people_search_html(self, html: str) -> list[LinkedInProfileResult]:
        """Parse people search results from HTML.

        Args:
            html: Raw HTML from search results page

        Returns:
            List of parsed profile results
        """
        soup = BeautifulSoup(html, "html.parser")
        profiles: list[LinkedInProfileResult] = []

        # Find profile cards
        profile_cards = soup.select(
            "li.reusable-search__result-container, "
            "div.entity-result"
        )

        for card in profile_cards:
            try:
                profile = self._parse_single_profile_card(card)
                if profile:
                    profiles.append(profile)
            except Exception as e:
                logger.warning(f"Failed to parse profile card: {e}")
                continue

        return profiles

    def _parse_single_profile_card(
        self,
        card: BeautifulSoup,
    ) -> LinkedInProfileResult | None:
        """Parse a single profile card element.

        Args:
            card: BeautifulSoup element for the profile card

        Returns:
            Parsed profile result or None if parsing fails
        """
        # Extract profile link and ID
        profile_link = card.select_one(
            "a.app-aware-link, "
            "a.entity-result__title-link"
        )
        if not profile_link:
            return None

        profile_url = profile_link.get("href", "")
        profile_id = ""

        # Extract profile ID from URL
        match = re.search(r"/in/([^/\?]+)", profile_url)
        if match:
            profile_id = match.group(1)
        else:
            return None

        # Extract name
        name_el = card.select_one(
            "span.entity-result__title-text a span[aria-hidden='true'], "
            "span.entity-result__title-text"
        )
        full_name = name_el.get_text(strip=True) if name_el else "Unknown"

        # Extract headline
        headline_el = card.select_one(
            "div.entity-result__primary-subtitle, "
            "p.entity-result__summary"
        )
        headline = headline_el.get_text(strip=True) if headline_el else None

        # Extract location
        location_el = card.select_one("div.entity-result__secondary-subtitle")
        location = location_el.get_text(strip=True) if location_el else None

        # Extract profile picture
        img_el = card.select_one("img.presence-entity__image, img.entity-result__image")
        profile_picture_url = (
            img_el.get("data-delayed-url") or img_el.get("src") if img_el else None
        )

        # Extract connection degree
        degree_el = card.select_one("span.entity-result__badge-text")
        connection_degree = degree_el.get_text(strip=True) if degree_el else None

        # Parse current company and title from headline
        current_company = None
        current_title = None
        if headline:
            # Common pattern: "Title at Company"
            if " at " in headline:
                parts = headline.split(" at ", 1)
                current_title = parts[0].strip()
                current_company = parts[1].strip()
            else:
                current_title = headline

        # Check for Premium badge
        is_premium = bool(card.select_one("li-icon[type='linkedin-premium-gold-icon']"))

        # Check for Open to Work badge
        is_open_to_work = bool(
            card.select_one("span.entity-result__open-to-work-badge")
            or "open to work" in (headline or "").lower()
        )

        return LinkedInProfileResult(
            profile_id=profile_id,
            full_name=full_name,
            headline=headline,
            location=location,
            profile_url=profile_url,
            profile_picture_url=profile_picture_url,
            current_company=current_company,
            current_title=current_title,
            connection_degree=connection_degree,
            is_premium=is_premium,
            is_open_to_work=is_open_to_work,
        )

    async def get_profile_details(self, profile_id: str) -> dict[str, Any]:
        """Fetch detailed information for a specific profile.

        Args:
            profile_id: LinkedIn profile ID (public identifier)

        Returns:
            Dictionary with profile details

        Raises:
            AuthenticationError: Session required for profile details
        """
        if not self._authenticated:
            raise AuthenticationError(
                "Profile details require authentication. Please provide a valid li_at cookie."
            )

        url = f"{self.BASE_URL}/in/{profile_id}/"

        response = await self._make_request("GET", url)
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        details: dict[str, Any] = {
            "profile_id": profile_id,
            "url": url,
        }

        # Name
        name_el = soup.select_one("h1.text-heading-xlarge")
        details["full_name"] = name_el.get_text(strip=True) if name_el else None

        # Headline
        headline_el = soup.select_one("div.text-body-medium")
        details["headline"] = headline_el.get_text(strip=True) if headline_el else None

        # Location
        location_el = soup.select_one("span.text-body-small")
        details["location"] = location_el.get_text(strip=True) if location_el else None

        # About section
        about_el = soup.select_one("div.pv-shared-text-with-see-more")
        if about_el:
            details["about"] = about_el.get_text(separator=" ", strip=True)

        # Experience section
        experience_section = soup.select("section.experience-section li")
        experiences = []
        for exp in experience_section[:5]:  # Limit to 5 most recent
            exp_data = {
                "title": None,
                "company": None,
                "duration": None,
            }
            title_el = exp.select_one("h3.profile-section-card__title")
            exp_data["title"] = title_el.get_text(strip=True) if title_el else None

            company_el = exp.select_one("h4.profile-section-card__subtitle")
            exp_data["company"] = (
                company_el.get_text(strip=True) if company_el else None
            )

            duration_el = exp.select_one("span.date-range")
            exp_data["duration"] = (
                duration_el.get_text(strip=True) if duration_el else None
            )

            if exp_data["title"]:
                experiences.append(exp_data)

        details["experiences"] = experiences

        return details

    # =========================================================================
    # Company Search
    # =========================================================================

    async def search_companies(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[LinkedInCompanyInfo]:
        """Search for companies on LinkedIn.

        Args:
            query: Company name or keywords
            max_results: Maximum number of results

        Returns:
            List of company results
        """
        logger.info(f"Searching companies: {query}")

        url = f"{self.BASE_URL}/search/results/companies/?keywords={quote_plus(query)}"

        response = await self._make_request("GET", url)
        html = response.text

        soup = BeautifulSoup(html, "html.parser")
        companies: list[LinkedInCompanyInfo] = []

        company_cards = soup.select(
            "li.reusable-search__result-container, "
            "div.entity-result"
        )

        for card in company_cards[:max_results]:
            try:
                # Extract company link and ID
                link_el = card.select_one("a.app-aware-link")
                if not link_el:
                    continue

                company_url = link_el.get("href", "")
                match = re.search(r"/company/([^/\?]+)", company_url)
                if not match:
                    continue

                company_id = match.group(1)

                # Extract company name
                name_el = card.select_one("span.entity-result__title-text a")
                name = name_el.get_text(strip=True) if name_el else "Unknown"

                # Extract industry
                industry_el = card.select_one("div.entity-result__primary-subtitle")
                industry = industry_el.get_text(strip=True) if industry_el else None

                # Extract company size/info
                size_el = card.select_one("div.entity-result__secondary-subtitle")
                company_size = size_el.get_text(strip=True) if size_el else None

                # Extract logo
                logo_el = card.select_one("img.entity-result__image")
                logo_url = (
                    logo_el.get("data-delayed-url") or logo_el.get("src")
                    if logo_el
                    else None
                )

                companies.append(
                    LinkedInCompanyInfo(
                        company_id=company_id,
                        name=name,
                        industry=industry,
                        company_size=company_size,
                        company_url=company_url,
                        logo_url=logo_url,
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to parse company card: {e}")
                continue

        return companies

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_rate_limit_status(self) -> RateLimitStatus:
        """Get current rate limit status.

        Returns:
            RateLimitStatus with current usage information
        """
        return self.rate_limiter.get_status()

    async def validate_session(self) -> bool:
        """Validate the current session cookie.

        Returns:
            True if session is valid, False otherwise
        """
        if not self.session_cookie:
            return False

        try:
            # Try to access a page that requires authentication
            response = await self._make_request(
                "GET", f"{self.BASE_URL}/feed/"
            )
            # If we get redirected to login, session is invalid
            return "login" not in str(response.url)
        except AuthenticationError:
            return False
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False


# =============================================================================
# Convenience Functions
# =============================================================================


async def search_linkedin_jobs(
    keywords: str,
    location: str | None = None,
    experience_levels: list[ExperienceLevel] | None = None,
    date_posted: DatePosted = DatePosted.ANY_TIME,
    remote_options: list[RemoteOption] | None = None,
    max_results: int = 25,
    session_cookie: str | None = None,
) -> list[LinkedInJobResult]:
    """Convenience function to search LinkedIn jobs.

    Args:
        keywords: Search keywords
        location: Location filter
        experience_levels: Experience level filters
        date_posted: Date posted filter
        remote_options: Remote work options
        max_results: Maximum results to return
        session_cookie: Optional LinkedIn session cookie for authenticated search

    Returns:
        List of job results
    """
    config = LinkedInSearchConfig(
        keywords=keywords,
        location=location,
        experience_levels=experience_levels or [],
        date_posted=date_posted,
        remote_options=remote_options or [],
        max_results=max_results,
    )

    async with LinkedInScraper(session_cookie=session_cookie) as scraper:
        return await scraper.search_jobs(config)


async def find_recruiters_at_company(
    company_name: str,
    session_cookie: str,
    max_results: int = 10,
) -> list[LinkedInProfileResult]:
    """Find recruiters and hiring managers at a specific company.

    Args:
        company_name: Name of the company
        session_cookie: LinkedIn session cookie (required)
        max_results: Maximum results to return

    Returns:
        List of recruiter/hiring manager profiles
    """
    async with LinkedInScraper(session_cookie=session_cookie) as scraper:
        # Search for recruiters
        recruiters = await scraper.search_people(
            keywords="recruiter OR talent acquisition OR hiring manager",
            company=company_name,
            max_results=max_results,
        )
        return recruiters
