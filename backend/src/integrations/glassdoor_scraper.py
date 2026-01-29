"""Glassdoor scraper integration for job search.

This module provides async Glassdoor scraping capabilities including:
- Job search with filters (keywords, location, salary, company rating, job type)
- Pagination support for fetching multiple results
- Anti-detection measures (user agent rotation, request delays)

IMPORTANT: Glassdoor's Terms of Service should be reviewed before using this scraper.
Web scraping may violate their ToS. Use responsibly and respect rate limits.
"""

import asyncio
import logging
import random
import re
import time
from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import quote_plus, urlencode, urljoin

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Enums for Glassdoor Search Filters
# =============================================================================


class JobType(str, Enum):
    """Glassdoor job type filters."""

    FULL_TIME = "fulltime"
    PART_TIME = "parttime"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"


class SalaryRange(str, Enum):
    """Glassdoor salary range filters (annual USD)."""

    RANGE_40K_PLUS = "40000"
    RANGE_60K_PLUS = "60000"
    RANGE_80K_PLUS = "80000"
    RANGE_100K_PLUS = "100000"
    RANGE_120K_PLUS = "120000"
    RANGE_140K_PLUS = "140000"
    RANGE_160K_PLUS = "160000"
    RANGE_180K_PLUS = "180000"
    RANGE_200K_PLUS = "200000"


class CompanyRating(str, Enum):
    """Glassdoor minimum company rating filters."""

    RATING_2_PLUS = "2.0"
    RATING_2_5_PLUS = "2.5"
    RATING_3_PLUS = "3.0"
    RATING_3_5_PLUS = "3.5"
    RATING_4_PLUS = "4.0"


class DatePosted(str, Enum):
    """Glassdoor date posted filters."""

    LAST_24_HOURS = "1"
    LAST_3_DAYS = "3"
    LAST_WEEK = "7"
    LAST_2_WEEKS = "14"
    LAST_MONTH = "30"
    ANY_TIME = ""


class RemoteOption(str, Enum):
    """Glassdoor remote work filters."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "onsite"


# =============================================================================
# Pydantic Models
# =============================================================================


class GlassdoorSearchConfig(BaseModel):
    """Configuration for Glassdoor job search."""

    keywords: str = Field(..., description="Search keywords")
    location: str | None = Field(None, description="Location filter (city, state, or country)")
    salary_min: int | None = Field(None, ge=0, description="Minimum salary filter (annual USD)")
    company_rating_min: CompanyRating | None = Field(
        None, description="Minimum company rating filter"
    )
    job_types: list[JobType] = Field(default_factory=list, description="Job type filters")
    date_posted: DatePosted = Field(
        default=DatePosted.ANY_TIME, description="Date posted filter"
    )
    remote_options: list[RemoteOption] = Field(
        default_factory=list, description="Remote work options"
    )
    easy_apply_only: bool = Field(False, description="Only show Easy Apply jobs")
    max_results: int = Field(30, ge=1, le=100, description="Maximum results to fetch")


class GlassdoorJobResult(BaseModel):
    """Represents a Glassdoor job listing."""

    job_id: str = Field(..., description="Glassdoor job ID")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    company_rating: float | None = Field(None, description="Company rating (1-5)")
    location: str | None = Field(None, description="Job location")
    salary_range: str | None = Field(None, description="Salary range if available")
    description_snippet: str | None = Field(None, description="Short description snippet")
    job_url: str = Field(..., description="Direct URL to job posting")
    posted_date: str | None = Field(None, description="When the job was posted")
    is_remote: bool = Field(False, description="Whether job is remote")
    employment_type: str | None = Field(None, description="Full-time, Part-time, etc.")
    company_logo_url: str | None = Field(None, description="Company logo URL")
    benefits_snippet: str | None = Field(None, description="Benefits mentioned")
    easy_apply: bool = Field(False, description="Whether Easy Apply is available")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("job_url", mode="before")
    @classmethod
    def ensure_full_url(cls, v: str) -> str:
        """Ensure job URL is a full URL."""
        if v and not v.startswith("http"):
            return f"https://www.glassdoor.com{v}"
        return v

    @field_validator("company_rating", mode="before")
    @classmethod
    def parse_rating(cls, v: Any) -> float | None:
        """Parse company rating to float."""
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v.strip())
            except ValueError:
                return None
        return None


class RateLimitStatus(BaseModel):
    """Rate limiting status."""

    requests_made: int = Field(0, description="Requests made in current window")
    requests_remaining: int = Field(30, description="Requests remaining in current window")
    window_reset_time: datetime | None = Field(None, description="When the rate limit window resets")
    is_rate_limited: bool = Field(False, description="Whether currently rate limited")
    tokens_available: float = Field(30.0, description="Current tokens in bucket")


# =============================================================================
# Rate Limiter (Token Bucket Pattern)
# =============================================================================


class TokenBucketRateLimiter:
    """Token bucket rate limiter for Glassdoor requests.

    Implements a token bucket algorithm with:
    - Configurable bucket capacity (max burst)
    - Configurable refill rate
    - Random delays between requests for anti-detection
    """

    def __init__(
        self,
        capacity: float = 30.0,
        refill_rate: float = 0.5,  # tokens per second (30 per minute)
        min_delay_seconds: float = 3.0,
        max_delay_seconds: float = 10.0,
    ):
        """Initialize token bucket rate limiter.

        Args:
            capacity: Maximum tokens the bucket can hold (burst limit).
            refill_rate: Tokens added per second.
            min_delay_seconds: Minimum delay between requests.
            max_delay_seconds: Maximum delay between requests.
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds
        self._tokens = capacity
        self._last_refill_time = time.time()
        self._request_count = 0
        self._window_start = time.time()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill_time
        tokens_to_add = elapsed * self.refill_rate
        self._tokens = min(self.capacity, self._tokens + tokens_to_add)
        self._last_refill_time = now

        # Reset request count every hour
        if now - self._window_start >= 3600:
            self._request_count = 0
            self._window_start = now

    async def acquire(self, tokens: float = 1.0) -> float:
        """Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            The delay (in seconds) that was waited.

        Raises:
            RateLimitExceeded: If rate limit is exceeded and cannot acquire tokens.
        """
        async with self._lock:
            self._refill()

            if self._tokens < tokens:
                wait_time = (tokens - self._tokens) / self.refill_rate
                if wait_time > 60:  # Don't wait more than 60 seconds
                    raise RateLimitExceeded(
                        f"Rate limit exceeded. Need to wait {wait_time:.1f} seconds. "
                        f"Tokens available: {self._tokens:.2f}"
                    )
                logger.info(f"Rate limiter waiting {wait_time:.1f}s for tokens")
                await asyncio.sleep(wait_time)
                self._refill()

            self._tokens -= tokens
            self._request_count += 1

            # Add random delay for anti-detection
            delay = random.uniform(self.min_delay, self.max_delay)
            await asyncio.sleep(delay)

            return delay

    def get_status(self) -> RateLimitStatus:
        """Get current rate limit status."""
        self._refill()

        requests_per_hour = 30  # Estimated max safe requests per hour
        requests_remaining = max(0, requests_per_hour - self._request_count)

        window_reset = None
        if self._request_count > 0:
            window_reset = datetime.fromtimestamp(self._window_start + 3600)

        return RateLimitStatus(
            requests_made=self._request_count,
            requests_remaining=requests_remaining,
            window_reset_time=window_reset,
            is_rate_limited=self._tokens < 1.0,
            tokens_available=self._tokens,
        )


# =============================================================================
# Exceptions
# =============================================================================


class GlassdoorScraperError(Exception):
    """Base exception for Glassdoor scraper."""

    pass


class RateLimitExceeded(GlassdoorScraperError):
    """Raised when rate limit is exceeded."""

    pass


class ScrapingError(GlassdoorScraperError):
    """Raised when scraping fails."""

    pass


class ParsingError(GlassdoorScraperError):
    """Raised when HTML parsing fails."""

    pass


class BlockedError(GlassdoorScraperError):
    """Raised when Glassdoor blocks the request (CAPTCHA, etc.)."""

    pass


class NetworkError(GlassdoorScraperError):
    """Raised when network request fails."""

    pass


# =============================================================================
# User Agent Rotation
# =============================================================================


class UserAgentRotator:
    """Rotates through realistic user agents for anti-detection."""

    USER_AGENTS = [
        # Chrome on macOS (most recent versions)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    ]

    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-US,en;q=0.9,es;q=0.8",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.9,fr;q=0.8",
        "en-US,en;q=0.8",
    ]

    def __init__(self):
        """Initialize user agent rotator."""
        self._current_index = random.randint(0, len(self.USER_AGENTS) - 1)
        self._current_ua = self.USER_AGENTS[self._current_index]

    def get_random(self) -> str:
        """Get a random user agent."""
        return random.choice(self.USER_AGENTS)

    def get_next(self) -> str:
        """Get the next user agent in rotation."""
        self._current_index = (self._current_index + 1) % len(self.USER_AGENTS)
        self._current_ua = self.USER_AGENTS[self._current_index]
        return self._current_ua

    def get_current(self) -> str:
        """Get the current user agent."""
        return self._current_ua

    def get_random_accept_language(self) -> str:
        """Get a random Accept-Language header value."""
        return random.choice(self.ACCEPT_LANGUAGES)


# =============================================================================
# Glassdoor Scraper
# =============================================================================


class GlassdoorScraper:
    """Async Glassdoor scraper with rate limiting and anti-detection.

    This scraper provides functionality for:
    - Job search with comprehensive filters (keywords, location, salary, rating, job type)
    - Pagination support for fetching multiple pages of results
    - Anti-detection measures (user agent rotation, realistic headers, delays)

    Example usage:
        async with GlassdoorScraper() as scraper:
            jobs = await scraper.search_jobs(
                GlassdoorSearchConfig(
                    keywords="Software Engineer",
                    location="San Francisco, CA",
                    salary_min=100000,
                    company_rating_min=CompanyRating.RATING_3_5_PLUS,
                )
            )
    """

    BASE_URL = "https://www.glassdoor.com"
    JOBS_SEARCH_URL = "https://www.glassdoor.com/Job/jobs.htm"

    def __init__(
        self,
        rate_limiter: TokenBucketRateLimiter | None = None,
        proxy: str | None = None,
    ):
        """Initialize Glassdoor scraper.

        Args:
            rate_limiter: Optional custom rate limiter.
            proxy: Optional proxy URL for requests.
        """
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter()
        self.user_agent_rotator = UserAgentRotator()
        self.proxy = proxy
        self._client: httpx.AsyncClient | None = None
        self._session_cookies: dict[str, str] = {}

    async def __aenter__(self) -> "GlassdoorScraper":
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

        transport = None
        if self.proxy:
            transport = httpx.AsyncHTTPTransport(proxy=self.proxy)

        self._client = httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=30.0,
            transport=transport,
        )

        # Warm up the session by visiting the homepage first
        try:
            await self._warm_up_session()
        except Exception as e:
            logger.warning(f"Session warm-up failed: {e}")

        logger.info("Glassdoor scraper initialized")

    async def _warm_up_session(self) -> None:
        """Visit homepage to establish cookies and session."""
        client = await self._get_client()
        try:
            response = await client.get(self.BASE_URL)
            # Store any cookies set by Glassdoor
            for cookie in response.cookies.jar:
                self._session_cookies[cookie.name] = cookie.value
            logger.debug(f"Session cookies established: {list(self._session_cookies.keys())}")
        except Exception as e:
            logger.debug(f"Warm-up request failed: {e}")

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with anti-detection measures."""
        ua = self.user_agent_rotator.get_current()
        accept_lang = self.user_agent_rotator.get_random_accept_language()

        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": accept_lang,
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }

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
        logger.info("Glassdoor scraper closed")

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
            BlockedError: If Glassdoor blocks the request
            ScrapingError: If request fails
        """
        # Apply rate limiting
        delay = await self.rate_limiter.acquire()
        logger.debug(f"Rate limiter applied {delay:.1f}s delay")

        client = await self._get_client()

        # Occasionally rotate user agent
        if random.random() < 0.25:  # 25% chance to rotate
            new_ua = self.user_agent_rotator.get_next()
            client.headers["User-Agent"] = new_ua
            logger.debug(f"Rotated user agent")

        # Add referer header for subsequent requests
        if "Referer" not in kwargs.get("headers", {}):
            kwargs.setdefault("headers", {})["Referer"] = self.BASE_URL

        try:
            response = await client.request(method, url, **kwargs)

            # Check for blocking/CAPTCHA
            if response.status_code == 403:
                raise BlockedError(
                    "Access forbidden. Glassdoor may have detected automated access. "
                    "Try using a different IP or waiting before retrying."
                )
            if response.status_code == 429:
                raise RateLimitExceeded(
                    "Glassdoor rate limit hit. Please wait before making more requests."
                )

            # Check for CAPTCHA in response
            if self._is_captcha_page(response.text):
                raise BlockedError(
                    "CAPTCHA detected. Glassdoor is blocking automated access. "
                    "Consider using a different IP or reducing request frequency."
                )

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {url}")
            raise ScrapingError(f"Request failed with status {e.response.status_code}: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise NetworkError(f"Network request failed: {e}")

    def _is_captcha_page(self, html: str) -> bool:
        """Check if the response is a CAPTCHA page.

        Args:
            html: Response HTML

        Returns:
            True if CAPTCHA is detected
        """
        captcha_indicators = [
            "captcha",
            "challenge-running",
            "cf-browser-verification",
            "recaptcha",
            "hcaptcha",
            "please verify you are a human",
            "access denied",
            "blocked",
        ]
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in captcha_indicators)

    # =========================================================================
    # Job Search
    # =========================================================================

    def _build_job_search_params(
        self,
        config: GlassdoorSearchConfig,
        page: int = 1,
    ) -> dict[str, str]:
        """Build query parameters for job search.

        Args:
            config: Search configuration
            page: Page number (1-indexed)

        Returns:
            Dictionary of query parameters
        """
        params: dict[str, str] = {
            "sc.keyword": config.keywords,
        }

        if config.location:
            params["locT"] = "C"  # City type
            params["locId"] = ""  # Will be resolved by Glassdoor
            params["locKeyword"] = config.location

        # Job types filter
        if config.job_types:
            job_type_values = [jt.value for jt in config.job_types]
            params["jobType"] = ",".join(job_type_values)

        # Salary filter
        if config.salary_min:
            params["minSalary"] = str(config.salary_min)

        # Company rating filter
        if config.company_rating_min:
            params["minRating"] = config.company_rating_min.value

        # Date posted filter
        if config.date_posted and config.date_posted != DatePosted.ANY_TIME:
            params["fromAge"] = config.date_posted.value

        # Remote options
        if config.remote_options:
            remote_values = [ro.value for ro in config.remote_options]
            params["remoteWorkType"] = ",".join(remote_values)

        # Easy Apply filter
        if config.easy_apply_only:
            params["applicationType"] = "1"

        # Pagination
        if page > 1:
            params["p"] = str(page)

        return params

    def _build_search_url(self, config: GlassdoorSearchConfig, page: int = 1) -> str:
        """Build the full search URL with proper formatting.

        Args:
            config: Search configuration
            page: Page number

        Returns:
            Full search URL
        """
        # Glassdoor uses a specific URL format for job searches
        keyword_slug = quote_plus(config.keywords.replace(" ", "-").lower())

        base_path = f"/Job/{keyword_slug}-jobs-SRCH_KO0,{len(config.keywords)}.htm"

        params = self._build_job_search_params(config, page)

        # Remove keyword from params since it's in the URL path
        params.pop("sc.keyword", None)

        if params:
            query_string = urlencode(params)
            return f"{self.BASE_URL}{base_path}?{query_string}"

        return f"{self.BASE_URL}{base_path}"

    async def search_jobs(
        self,
        config: GlassdoorSearchConfig,
    ) -> list[GlassdoorJobResult]:
        """Search for jobs on Glassdoor.

        Args:
            config: Search configuration with keywords, filters, etc.

        Returns:
            List of job results matching the search criteria.

        Raises:
            BlockedError: If Glassdoor blocks the request
            RateLimitExceeded: If rate limit is exceeded
            ScrapingError: If scraping fails
        """
        logger.info(f"Searching Glassdoor jobs: {config.keywords} in {config.location}")

        jobs: list[GlassdoorJobResult] = []
        page = 1
        max_pages = (config.max_results // 30) + 1  # ~30 jobs per page
        consecutive_empty_pages = 0
        max_consecutive_empty = 2

        while len(jobs) < config.max_results and page <= max_pages:
            try:
                page_jobs = await self._fetch_job_page(config, page)

                if not page_jobs:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_consecutive_empty:
                        logger.info(f"No more results after page {page}")
                        break
                else:
                    consecutive_empty_pages = 0
                    jobs.extend(page_jobs)
                    logger.info(f"Page {page}: Found {len(page_jobs)} jobs (total: {len(jobs)})")

                page += 1

                # Add extra random delay between pages
                if len(jobs) < config.max_results and page <= max_pages:
                    inter_page_delay = random.uniform(2.0, 5.0)
                    await asyncio.sleep(inter_page_delay)

            except (BlockedError, RateLimitExceeded):
                raise
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= max_consecutive_empty:
                    break
                page += 1

        # Trim to max_results
        jobs = jobs[: config.max_results]

        logger.info(f"Search complete. Found {len(jobs)} total jobs")
        return jobs

    async def _fetch_job_page(
        self,
        config: GlassdoorSearchConfig,
        page: int,
    ) -> list[GlassdoorJobResult]:
        """Fetch a single page of job results.

        Args:
            config: Search configuration
            page: Page number

        Returns:
            List of jobs from this page
        """
        url = self._build_search_url(config, page)
        logger.debug(f"Fetching: {url}")

        response = await self._make_request("GET", url)
        html = response.text

        return self._parse_job_listings(html)

    def _parse_job_listings(self, html: str) -> list[GlassdoorJobResult]:
        """Parse job listings from HTML response.

        Args:
            html: Raw HTML from Glassdoor

        Returns:
            List of parsed job results
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[GlassdoorJobResult] = []

        # Glassdoor uses various selectors for job cards
        # Try multiple patterns to handle different page layouts
        job_cards = soup.select(
            "li.react-job-listing, "
            "div[data-test='jobListing'], "
            "article.job-listing, "
            "div.JobsList_jobListItem__JBBUV, "
            "li[data-jobid], "
            "div[data-id]"
        )

        if not job_cards:
            # Try finding job cards in JSON-LD data
            jobs.extend(self._parse_json_ld_jobs(soup))

            # Also try script tag with job data
            jobs.extend(self._parse_script_job_data(soup))

        for card in job_cards:
            try:
                job = self._parse_single_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job card: {e}")
                continue

        return jobs

    def _parse_single_job_card(self, card: BeautifulSoup) -> GlassdoorJobResult | None:
        """Parse a single job card element.

        Args:
            card: BeautifulSoup element for the job card

        Returns:
            Parsed job result or None if parsing fails
        """
        # Extract job ID from data attributes
        job_id = (
            card.get("data-id")
            or card.get("data-jobid")
            or card.get("data-job-id")
            or card.get("id", "").replace("job-listing-", "")
        )

        if not job_id:
            # Try to extract from link
            link_el = card.select_one("a[href*='/job-listing/'], a[href*='/partner/']")
            if link_el:
                href = link_el.get("href", "")
                match = re.search(r"jobListingId=(\d+)|/(\d+)\.htm", href)
                if match:
                    job_id = match.group(1) or match.group(2)

        if not job_id:
            return None

        # Extract job URL
        job_url = ""
        link_el = card.select_one(
            "a[data-test='job-link'], "
            "a.jobLink, "
            "a.JobCard_jobTitle__GLyJ1, "
            "a[href*='/job-listing/']"
        )
        if link_el:
            job_url = link_el.get("href", "")
            if job_url and not job_url.startswith("http"):
                job_url = urljoin(self.BASE_URL, job_url)

        if not job_url:
            job_url = f"{self.BASE_URL}/job-listing/?jl={job_id}"

        # Extract title
        title_el = card.select_one(
            "a[data-test='job-link'], "
            "a.jobLink, "
            "div.job-title, "
            "span.JobCard_jobTitle__GLyJ1, "
            "h2 a, "
            "[class*='jobTitle']"
        )
        title = title_el.get_text(strip=True) if title_el else "Unknown Title"

        # Extract company name
        company_el = card.select_one(
            "span[data-test='employer-name'], "
            "div.employer-name, "
            "span.EmployerProfile_employerName__twNzy, "
            "[class*='employer'], "
            "[class*='companyName']"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown Company"
        # Clean up company name (remove rating if included)
        company = re.sub(r"\s*\d+\.\d+\s*$", "", company)

        # Extract company rating
        rating_el = card.select_one(
            "span[data-test='employer-rating'], "
            "span.rating, "
            "span.EmployerProfile_ratingValue__MjI6O, "
            "[class*='rating']"
        )
        company_rating = None
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            try:
                company_rating = float(rating_text)
            except ValueError:
                match = re.search(r"(\d+\.?\d*)", rating_text)
                if match:
                    company_rating = float(match.group(1))

        # Extract location
        location_el = card.select_one(
            "span[data-test='emp-location'], "
            "span.location, "
            "span.JobCard_location__rCz3x, "
            "[class*='location']"
        )
        location = location_el.get_text(strip=True) if location_el else None

        # Check for remote
        is_remote = False
        if location:
            is_remote = "remote" in location.lower()
        remote_badge = card.select_one("[class*='remote'], [data-test*='remote']")
        if remote_badge:
            is_remote = True

        # Extract salary
        salary_el = card.select_one(
            "span[data-test='detailSalary'], "
            "span.salary-estimate, "
            "span.JobCard_salaryEstimate__QnAkY, "
            "[class*='salary'], "
            "[class*='compensation']"
        )
        salary_range = salary_el.get_text(strip=True) if salary_el else None

        # Extract posted date
        posted_el = card.select_one(
            "div[data-test='job-age'], "
            "span.job-age, "
            "span.JobCard_listingAge__KuaxZ, "
            "[class*='listingAge'], "
            "[class*='posted']"
        )
        posted_date = posted_el.get_text(strip=True) if posted_el else None

        # Extract description snippet
        desc_el = card.select_one(
            "div[data-test='job-snippet'], "
            "div.job-snippet, "
            "div.JobCard_jobDescriptionSnippet__l1tnl, "
            "[class*='description'], "
            "[class*='snippet']"
        )
        description_snippet = desc_el.get_text(strip=True) if desc_el else None

        # Extract employment type
        employment_type = None
        type_el = card.select_one(
            "[data-test='job-type'], "
            "[class*='jobType'], "
            "[class*='employmentType']"
        )
        if type_el:
            employment_type = type_el.get_text(strip=True)
        elif description_snippet:
            # Try to extract from description
            type_patterns = ["full-time", "part-time", "contract", "temporary", "internship"]
            for pattern in type_patterns:
                if pattern in description_snippet.lower():
                    employment_type = pattern.title()
                    break

        # Extract company logo
        logo_el = card.select_one("img.employer-logo, img[alt*='logo'], img[class*='logo']")
        company_logo_url = logo_el.get("src") if logo_el else None

        # Check for Easy Apply
        easy_apply = bool(
            card.select_one(
                "[data-test='easy-apply-badge'], "
                "[class*='easyApply'], "
                "[class*='EasyApply']"
            )
        )

        return GlassdoorJobResult(
            job_id=str(job_id),
            title=title,
            company=company,
            company_rating=company_rating,
            location=location,
            salary_range=salary_range,
            description_snippet=description_snippet,
            job_url=job_url,
            posted_date=posted_date,
            is_remote=is_remote,
            employment_type=employment_type,
            company_logo_url=company_logo_url,
            easy_apply=easy_apply,
        )

    def _parse_json_ld_jobs(self, soup: BeautifulSoup) -> list[GlassdoorJobResult]:
        """Parse jobs from JSON-LD structured data.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of jobs found in JSON-LD
        """
        import json

        jobs = []
        scripts = soup.select('script[type="application/ld+json"]')

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Handle single job or list of jobs
                job_postings = []
                if isinstance(data, dict):
                    if data.get("@type") == "JobPosting":
                        job_postings = [data]
                    elif "@graph" in data:
                        job_postings = [
                            item for item in data["@graph"]
                            if item.get("@type") == "JobPosting"
                        ]
                elif isinstance(data, list):
                    job_postings = [
                        item for item in data
                        if isinstance(item, dict) and item.get("@type") == "JobPosting"
                    ]

                for job_data in job_postings:
                    try:
                        job = self._parse_json_ld_job(job_data)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.debug(f"Failed to parse JSON-LD job: {e}")

            except json.JSONDecodeError:
                continue

        return jobs

    def _parse_json_ld_job(self, data: dict) -> GlassdoorJobResult | None:
        """Parse a single job from JSON-LD data.

        Args:
            data: JSON-LD job posting data

        Returns:
            Parsed job result or None
        """
        job_id = data.get("identifier", {}).get("value", "")
        if not job_id:
            # Try to extract from URL
            url = data.get("url", "")
            match = re.search(r"jl=(\d+)|/(\d+)\.htm", url)
            if match:
                job_id = match.group(1) or match.group(2)
            else:
                job_id = str(hash(data.get("title", "") + data.get("url", "")))

        # Extract salary
        salary_range = None
        base_salary = data.get("baseSalary", {})
        if base_salary:
            salary_value = base_salary.get("value", {})
            if isinstance(salary_value, dict):
                min_val = salary_value.get("minValue", "")
                max_val = salary_value.get("maxValue", "")
                currency = base_salary.get("currency", "USD")
                if min_val and max_val:
                    salary_range = f"{currency} {min_val:,} - {max_val:,}"
                elif min_val:
                    salary_range = f"{currency} {min_val:,}+"

        # Extract location
        location = None
        job_location = data.get("jobLocation", {})
        if isinstance(job_location, dict):
            address = job_location.get("address", {})
            if isinstance(address, dict):
                parts = [
                    address.get("addressLocality", ""),
                    address.get("addressRegion", ""),
                    address.get("addressCountry", ""),
                ]
                location = ", ".join(filter(None, parts))
        elif isinstance(job_location, list) and job_location:
            address = job_location[0].get("address", {})
            if isinstance(address, dict):
                parts = [
                    address.get("addressLocality", ""),
                    address.get("addressRegion", ""),
                ]
                location = ", ".join(filter(None, parts))

        # Check for remote
        is_remote = False
        job_location_type = data.get("jobLocationType", "")
        if job_location_type and "remote" in str(job_location_type).lower():
            is_remote = True
        if location and "remote" in location.lower():
            is_remote = True

        # Extract company info
        hiring_org = data.get("hiringOrganization", {})
        company = hiring_org.get("name", "Unknown Company") if isinstance(hiring_org, dict) else "Unknown Company"
        company_logo_url = hiring_org.get("logo", None) if isinstance(hiring_org, dict) else None

        # Extract employment type
        employment_type = data.get("employmentType", None)
        if isinstance(employment_type, list):
            employment_type = employment_type[0] if employment_type else None

        # Extract posted date
        posted_date = data.get("datePosted", None)

        return GlassdoorJobResult(
            job_id=str(job_id),
            title=data.get("title", "Unknown Title"),
            company=company,
            company_rating=None,  # Not in JSON-LD
            location=location,
            salary_range=salary_range,
            description_snippet=data.get("description", "")[:300] if data.get("description") else None,
            job_url=data.get("url", ""),
            posted_date=posted_date,
            is_remote=is_remote,
            employment_type=employment_type,
            company_logo_url=company_logo_url,
            easy_apply=False,
        )

    def _parse_script_job_data(self, soup: BeautifulSoup) -> list[GlassdoorJobResult]:
        """Parse jobs from embedded script data.

        Glassdoor sometimes embeds job data in script tags.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of jobs found in scripts
        """
        import json

        jobs = []
        scripts = soup.select("script")

        for script in scripts:
            if not script.string:
                continue

            # Look for job data patterns in scripts
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                r'"jobListings":\s*(\[.*?\])',
                r'"jobs":\s*(\[.*?\])',
            ]

            for pattern in patterns:
                match = re.search(pattern, script.string, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))

                        # Extract jobs from the data structure
                        if isinstance(data, list):
                            for item in data:
                                job = self._extract_job_from_script_data(item)
                                if job:
                                    jobs.append(job)
                        elif isinstance(data, dict):
                            # Try common paths
                            job_list = (
                                data.get("jobListings")
                                or data.get("jobs")
                                or data.get("results")
                                or []
                            )
                            for item in job_list:
                                job = self._extract_job_from_script_data(item)
                                if job:
                                    jobs.append(job)
                    except json.JSONDecodeError:
                        continue

        return jobs

    def _extract_job_from_script_data(self, data: dict) -> GlassdoorJobResult | None:
        """Extract job information from script data object.

        Args:
            data: Job data dictionary

        Returns:
            Parsed job result or None
        """
        if not isinstance(data, dict):
            return None

        job_id = str(
            data.get("jobId")
            or data.get("id")
            or data.get("listingId")
            or ""
        )

        if not job_id:
            return None

        # Extract various fields
        title = (
            data.get("jobTitle")
            or data.get("title")
            or data.get("jobTitleText")
            or "Unknown Title"
        )

        company = (
            data.get("employer", {}).get("name")
            or data.get("companyName")
            or data.get("company")
            or "Unknown Company"
        )

        company_rating = (
            data.get("employer", {}).get("overallRating")
            or data.get("rating")
            or data.get("overallRating")
        )

        location = (
            data.get("location", {}).get("name")
            or data.get("locationName")
            or data.get("location")
        )
        if isinstance(location, dict):
            location = location.get("name")

        salary_range = data.get("salarySource") or data.get("salary")

        job_url = data.get("jobViewUrl") or data.get("url") or ""
        if job_url and not job_url.startswith("http"):
            job_url = urljoin(self.BASE_URL, job_url)

        return GlassdoorJobResult(
            job_id=job_id,
            title=title,
            company=company,
            company_rating=company_rating,
            location=location,
            salary_range=salary_range,
            description_snippet=data.get("jobDescription", "")[:300] if data.get("jobDescription") else None,
            job_url=job_url or f"{self.BASE_URL}/job-listing/?jl={job_id}",
            posted_date=data.get("listingAge") or data.get("ageInDays"),
            is_remote=bool(data.get("isRemote")) or "remote" in str(location or "").lower(),
            employment_type=data.get("jobType") or data.get("employmentType"),
            company_logo_url=data.get("employer", {}).get("squareLogoUrl"),
            easy_apply=bool(data.get("easyApply")),
        )

    async def get_job_details(self, job_id: str) -> dict[str, Any]:
        """Fetch detailed information for a specific job.

        Args:
            job_id: Glassdoor job ID

        Returns:
            Dictionary with full job details including description

        Raises:
            ScrapingError: If fetching details fails
        """
        url = f"{self.BASE_URL}/job-listing/job-jl{job_id}.htm"

        response = await self._make_request("GET", url)
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        details: dict[str, Any] = {"job_id": job_id, "url": url}

        # Title
        title_el = soup.select_one(
            "h1[data-test='job-title'], "
            "h1.jobTitle, "
            "[class*='JobTitle']"
        )
        details["title"] = title_el.get_text(strip=True) if title_el else None

        # Company
        company_el = soup.select_one(
            "span[data-test='employer-name'], "
            "div.employer-name, "
            "[class*='employerName']"
        )
        details["company"] = company_el.get_text(strip=True) if company_el else None

        # Location
        location_el = soup.select_one(
            "span[data-test='location'], "
            "div.location, "
            "[class*='location']"
        )
        details["location"] = location_el.get_text(strip=True) if location_el else None

        # Full description
        desc_el = soup.select_one(
            "div[data-test='job-description'], "
            "div.jobDescriptionContent, "
            "[class*='JobDescription']"
        )
        if desc_el:
            # Clean up the description
            for element in desc_el(["script", "style"]):
                element.decompose()
            details["description"] = desc_el.get_text(separator="\n", strip=True)
            details["description_html"] = str(desc_el)

        # Salary
        salary_el = soup.select_one(
            "span[data-test='detailSalary'], "
            "[class*='salary']"
        )
        details["salary_range"] = salary_el.get_text(strip=True) if salary_el else None

        # Company rating
        rating_el = soup.select_one(
            "span[data-test='employer-rating'], "
            "[class*='rating']"
        )
        if rating_el:
            try:
                details["company_rating"] = float(rating_el.get_text(strip=True))
            except ValueError:
                details["company_rating"] = None

        # Benefits
        benefits_section = soup.select(
            "div[data-test='benefits'] li, "
            "[class*='benefits'] li"
        )
        if benefits_section:
            details["benefits"] = [b.get_text(strip=True) for b in benefits_section]

        # Company overview
        overview_el = soup.select_one(
            "div[data-test='company-overview'], "
            "[class*='CompanyOverview']"
        )
        if overview_el:
            details["company_overview"] = overview_el.get_text(strip=True)

        return details

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_rate_limit_status(self) -> RateLimitStatus:
        """Get current rate limit status.

        Returns:
            RateLimitStatus with current usage information
        """
        return self.rate_limiter.get_status()


# =============================================================================
# Convenience Functions
# =============================================================================


async def search_glassdoor_jobs(
    keywords: str,
    location: str | None = None,
    salary_min: int | None = None,
    company_rating_min: CompanyRating | None = None,
    job_types: list[JobType] | None = None,
    date_posted: DatePosted = DatePosted.ANY_TIME,
    remote_options: list[RemoteOption] | None = None,
    max_results: int = 30,
) -> list[GlassdoorJobResult]:
    """Convenience function to search Glassdoor jobs.

    Args:
        keywords: Search keywords
        location: Location filter
        salary_min: Minimum salary filter
        company_rating_min: Minimum company rating filter
        job_types: Job type filters
        date_posted: Date posted filter
        remote_options: Remote work options
        max_results: Maximum results to return

    Returns:
        List of job results
    """
    config = GlassdoorSearchConfig(
        keywords=keywords,
        location=location,
        salary_min=salary_min,
        company_rating_min=company_rating_min,
        job_types=job_types or [],
        date_posted=date_posted,
        remote_options=remote_options or [],
        max_results=max_results,
    )

    async with GlassdoorScraper() as scraper:
        return await scraper.search_jobs(config)


async def get_glassdoor_job_details(job_id: str) -> dict[str, Any]:
    """Convenience function to get details for a specific job.

    Args:
        job_id: Glassdoor job ID

    Returns:
        Dictionary with job details
    """
    async with GlassdoorScraper() as scraper:
        return await scraper.get_job_details(job_id)
