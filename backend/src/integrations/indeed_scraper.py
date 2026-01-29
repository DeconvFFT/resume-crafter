"""Indeed job scraper integration for job search.

This module provides async Indeed job scraping capabilities including:
- Job search with filters (keywords, location, salary, job type, date posted, remote)
- Pagination support for fetching multiple results
- Anti-detection measures (user agent rotation, delays)

IMPORTANT: Indeed actively blocks automated scraping. This scraper implements
various anti-detection measures but may still be blocked. Use responsibly
and respect Indeed's Terms of Service.
"""

import asyncio
import hashlib
import logging
import random
import re
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from urllib.parse import quote_plus, urlencode, urljoin

import httpx
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Enums for Indeed Search Filters
# =============================================================================


class IndeedDatePosted(str, Enum):
    """Indeed date posted filters."""

    LAST_24_HOURS = "1"
    LAST_3_DAYS = "3"
    LAST_7_DAYS = "7"
    LAST_14_DAYS = "14"
    ANY_TIME = ""


class IndeedJobType(str, Enum):
    """Indeed job type filters."""

    FULL_TIME = "fulltime"
    PART_TIME = "parttime"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    COMMISSION = "commission"


class IndeedRemoteOption(str, Enum):
    """Indeed remote work filters."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = ""  # Default, no filter


class IndeedSalaryRange(str, Enum):
    """Indeed salary range filters (minimum salary)."""

    SALARY_20K = "20000"
    SALARY_40K = "40000"
    SALARY_60K = "60000"
    SALARY_80K = "80000"
    SALARY_100K = "100000"
    SALARY_120K = "120000"
    SALARY_140K = "140000"
    SALARY_160K = "160000"
    SALARY_180K = "180000"
    SALARY_200K = "200000"


class IndeedExperienceLevel(str, Enum):
    """Indeed experience level filters."""

    ENTRY_LEVEL = "entry_level"
    MID_LEVEL = "mid_level"
    SENIOR_LEVEL = "senior_level"
    NO_EXPERIENCE = "no_experience"


# =============================================================================
# Pydantic Models
# =============================================================================


class IndeedSearchConfig(BaseModel):
    """Configuration for Indeed job search."""

    keywords: str = Field(..., description="Search keywords")
    location: str | None = Field(None, description="Location filter (city, state, or zip)")
    salary_min: int | None = Field(None, ge=0, description="Minimum salary filter")
    job_types: list[IndeedJobType] = Field(default_factory=list, description="Job type filters")
    date_posted: IndeedDatePosted = Field(
        default=IndeedDatePosted.ANY_TIME, description="Date posted filter"
    )
    remote_option: IndeedRemoteOption = Field(
        default=IndeedRemoteOption.ON_SITE, description="Remote work filter"
    )
    experience_level: IndeedExperienceLevel | None = Field(
        None, description="Experience level filter"
    )
    radius_miles: int | None = Field(
        None, ge=0, le=100, description="Search radius in miles from location"
    )
    company: str | None = Field(None, description="Filter by company name")
    exclude_staffing: bool = Field(False, description="Exclude staffing agencies")
    max_results: int = Field(50, ge=1, le=200, description="Maximum results to fetch")


class IndeedJobResult(BaseModel):
    """Represents an Indeed job listing."""

    job_id: str = Field(..., description="Indeed job ID (jk parameter)")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str | None = Field(None, description="Job location")
    salary_range: str | None = Field(None, description="Salary range if available")
    description_snippet: str | None = Field(None, description="Short description snippet")
    job_url: str = Field(..., description="Direct URL to job posting")
    posted_date: str | None = Field(None, description="When the job was posted (relative)")
    is_remote: bool = Field(False, description="Whether job is remote")
    employment_type: str | None = Field(None, description="Full-time, Part-time, etc.")
    company_rating: float | None = Field(None, description="Company rating on Indeed")
    company_review_count: int | None = Field(None, description="Number of company reviews")
    is_easily_apply: bool = Field(False, description="Whether Easily Apply is available")
    is_urgently_hiring: bool = Field(False, description="Whether urgently hiring badge shown")
    benefits: list[str] = Field(default_factory=list, description="Listed benefits")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("job_url", mode="before")
    @classmethod
    def ensure_full_url(cls, v: str) -> str:
        """Ensure job URL is a full URL."""
        if v and not v.startswith("http"):
            return f"https://www.indeed.com{v}"
        return v


class IndeedJobDetails(BaseModel):
    """Detailed information for an Indeed job posting."""

    job_id: str = Field(..., description="Indeed job ID")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str | None = Field(None, description="Job location")
    salary_range: str | None = Field(None, description="Salary range")
    job_url: str = Field(..., description="URL to job posting")
    description_full: str | None = Field(None, description="Full job description")
    description_html: str | None = Field(None, description="Description HTML")
    posted_date: str | None = Field(None, description="Posted date")
    employment_type: str | None = Field(None, description="Employment type")
    qualifications: list[str] = Field(default_factory=list, description="Required qualifications")
    benefits: list[str] = Field(default_factory=list, description="Job benefits")
    is_remote: bool = Field(False, description="Whether remote")
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class RateLimitStatus(BaseModel):
    """Rate limiting status."""

    tokens_available: float = Field(..., description="Tokens currently available")
    max_tokens: float = Field(..., description="Maximum tokens in bucket")
    refill_rate: float = Field(..., description="Tokens refilled per second")
    is_rate_limited: bool = Field(False, description="Whether currently rate limited")
    next_available_in: float | None = Field(None, description="Seconds until next token available")


# =============================================================================
# Exceptions
# =============================================================================


class IndeedScraperError(Exception):
    """Base exception for Indeed scraper."""

    pass


class RateLimitExceeded(IndeedScraperError):
    """Raised when rate limit is exceeded."""

    pass


class ScrapingError(IndeedScraperError):
    """Raised when scraping fails."""

    pass


class BlockedError(IndeedScraperError):
    """Raised when Indeed blocks the request (CAPTCHA, etc.)."""

    pass


class ParsingError(IndeedScraperError):
    """Raised when HTML parsing fails."""

    pass


# =============================================================================
# Token Bucket Rate Limiter
# =============================================================================


class TokenBucketRateLimiter:
    """Token bucket rate limiter for Indeed requests.

    Implements a token bucket algorithm with:
    - Configurable bucket size (max burst)
    - Configurable refill rate (tokens per second)
    - Random jitter for anti-detection
    """

    def __init__(
        self,
        max_tokens: float = 10.0,
        refill_rate: float = 0.2,  # 1 token per 5 seconds = 12 requests/minute
        min_delay_seconds: float = 3.0,
        max_delay_seconds: float = 8.0,
    ):
        """Initialize token bucket rate limiter.

        Args:
            max_tokens: Maximum tokens in the bucket (burst capacity).
            refill_rate: Tokens added per second.
            min_delay_seconds: Minimum delay between requests.
            max_delay_seconds: Maximum delay between requests.
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.min_delay = min_delay_seconds
        self.max_delay = max_delay_seconds
        self._tokens = max_tokens
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(self.max_tokens, self._tokens + elapsed * self.refill_rate)
        self._last_update = now

    async def acquire(self, tokens: float = 1.0) -> float:
        """Acquire tokens to make a request.

        Args:
            tokens: Number of tokens to consume.

        Returns:
            The delay (in seconds) that was waited.

        Raises:
            RateLimitExceeded: If not enough tokens and cannot wait.
        """
        async with self._lock:
            self._refill()

            if self._tokens < tokens:
                # Calculate wait time for tokens to be available
                wait_time = (tokens - self._tokens) / self.refill_rate
                if wait_time > 60:  # Don't wait more than 60 seconds
                    raise RateLimitExceeded(
                        f"Rate limit exceeded. Need to wait {wait_time:.1f}s for tokens."
                    )
                logger.debug(f"Waiting {wait_time:.1f}s for rate limit tokens")
                await asyncio.sleep(wait_time)
                self._refill()

            self._tokens -= tokens

            # Add random delay for anti-detection
            delay = random.uniform(self.min_delay, self.max_delay)
            await asyncio.sleep(delay)

            return delay

    def get_status(self) -> RateLimitStatus:
        """Get current rate limit status."""
        self._refill()
        next_available = None
        if self._tokens < 1.0:
            next_available = (1.0 - self._tokens) / self.refill_rate

        return RateLimitStatus(
            tokens_available=self._tokens,
            max_tokens=self.max_tokens,
            refill_rate=self.refill_rate,
            is_rate_limited=self._tokens < 1.0,
            next_available_in=next_available,
        )


# =============================================================================
# User Agent Rotation
# =============================================================================


class UserAgentRotator:
    """Rotates through realistic user agents for anti-detection."""

    USER_AGENTS = [
        # Chrome on macOS (most common)
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    ]

    # Accept-Language variations
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-US,en;q=0.9,es;q=0.8",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.9,fr;q=0.8",
        "en,en-US;q=0.9",
    ]

    def __init__(self):
        """Initialize user agent rotator."""
        self._current_index = random.randint(0, len(self.USER_AGENTS) - 1)
        self._requests_with_current = 0
        self._max_requests_per_agent = random.randint(3, 7)

    def get_random(self) -> str:
        """Get a random user agent."""
        return random.choice(self.USER_AGENTS)

    def get_next(self) -> str:
        """Get the next user agent in rotation."""
        self._requests_with_current += 1
        if self._requests_with_current >= self._max_requests_per_agent:
            self._current_index = (self._current_index + 1) % len(self.USER_AGENTS)
            self._requests_with_current = 0
            self._max_requests_per_agent = random.randint(3, 7)
        return self.USER_AGENTS[self._current_index]

    def get_accept_language(self) -> str:
        """Get a random Accept-Language header."""
        return random.choice(self.ACCEPT_LANGUAGES)


# =============================================================================
# Indeed Scraper
# =============================================================================


class IndeedScraper:
    """Async Indeed job scraper with rate limiting and anti-detection.

    This scraper provides functionality for:
    - Job search with comprehensive filters
    - Pagination to fetch multiple pages of results
    - Anti-detection measures (user agent rotation, delays, headers)

    Indeed actively detects and blocks automated scraping. This scraper
    implements various anti-detection measures but may still be blocked.

    Example usage:
        async with IndeedScraper() as scraper:
            jobs = await scraper.search_jobs(
                IndeedSearchConfig(
                    keywords="Software Engineer",
                    location="San Francisco, CA",
                    salary_min=100000,
                    job_types=[IndeedJobType.FULL_TIME],
                    date_posted=IndeedDatePosted.LAST_7_DAYS,
                    remote_option=IndeedRemoteOption.REMOTE,
                )
            )
    """

    BASE_URL = "https://www.indeed.com"
    JOBS_SEARCH_URL = "https://www.indeed.com/jobs"

    def __init__(
        self,
        rate_limiter: TokenBucketRateLimiter | None = None,
        proxy: str | None = None,
    ):
        """Initialize Indeed scraper.

        Args:
            rate_limiter: Optional custom rate limiter. Defaults to token bucket.
            proxy: Optional proxy URL for requests.
        """
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter()
        self.proxy = proxy
        self.user_agent_rotator = UserAgentRotator()
        self._client: httpx.AsyncClient | None = None
        self._session_id = self._generate_session_id()

    def _generate_session_id(self) -> str:
        """Generate a realistic session ID."""
        return hashlib.md5(
            f"{time.time()}{random.random()}".encode()
        ).hexdigest()[:16]

    async def __aenter__(self) -> "IndeedScraper":
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

        # Warm up session with a visit to the main page
        try:
            await self._warm_up_session()
        except Exception as e:
            logger.warning(f"Session warm-up failed: {e}")

        logger.info("Indeed scraper initialized")

    async def _warm_up_session(self) -> None:
        """Visit Indeed homepage to establish a realistic session."""
        headers = self._build_headers()
        client = await self._get_client()
        client.headers.update(headers)

        try:
            await client.get(self.BASE_URL, timeout=15.0)
            await asyncio.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            logger.debug(f"Warm-up request failed: {e}")

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with anti-detection measures."""
        user_agent = self.user_agent_rotator.get_next()

        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": self.user_agent_rotator.get_accept_language(),
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
            "sec-ch-ua-platform": '"macOS"' if "Mac" in user_agent else '"Windows"',
            "DNT": "1",
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
        logger.info("Indeed scraper closed")

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
            BlockedError: If Indeed blocks the request
            ScrapingError: If request fails
        """
        # Apply rate limiting with token bucket
        delay = await self.rate_limiter.acquire()
        logger.debug(f"Rate limiter applied {delay:.1f}s delay")

        # Update headers with fresh user agent occasionally
        client = await self._get_client()
        if random.random() < 0.2:  # 20% chance to rotate
            client.headers["User-Agent"] = self.user_agent_rotator.get_next()
            client.headers["Accept-Language"] = self.user_agent_rotator.get_accept_language()

        # Add referer for subsequent requests
        if "Referer" not in kwargs.get("headers", {}):
            kwargs.setdefault("headers", {})
            kwargs["headers"]["Referer"] = self.BASE_URL

        try:
            response = await client.request(method, url, **kwargs)

            # Check for blocking/CAPTCHA
            if response.status_code == 403:
                raise BlockedError(
                    "Request blocked by Indeed. May require CAPTCHA or IP is blocked."
                )
            if response.status_code == 429:
                raise RateLimitExceeded(
                    "Indeed rate limit hit. Please wait before making more requests."
                )

            # Check for CAPTCHA in response
            if self._is_captcha_page(response.text):
                raise BlockedError(
                    "CAPTCHA detected. Indeed is blocking automated access."
                )

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {url}")
            raise ScrapingError(f"Request failed with status {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise ScrapingError(f"Request failed: {e}")

    def _is_captcha_page(self, html: str) -> bool:
        """Check if the response is a CAPTCHA page."""
        captcha_indicators = [
            "verify you are a human",
            "captcha",
            "unusual traffic",
            "automated access",
            "robot check",
            "hcaptcha",
            "recaptcha",
        ]
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in captcha_indicators)

    # =========================================================================
    # Job Search
    # =========================================================================

    def _build_search_params(
        self,
        config: IndeedSearchConfig,
        start: int = 0,
    ) -> dict[str, str]:
        """Build query parameters for job search.

        Args:
            config: Search configuration
            start: Pagination start offset (0, 10, 20, etc.)

        Returns:
            Dictionary of query parameters
        """
        params: dict[str, str] = {
            "q": config.keywords,
        }

        if config.location:
            params["l"] = config.location

        # Pagination (Indeed uses multiples of 10)
        if start > 0:
            params["start"] = str(start)

        # Date posted filter (fromage parameter)
        if config.date_posted and config.date_posted != IndeedDatePosted.ANY_TIME:
            params["fromage"] = config.date_posted.value

        # Job type filter (jt parameter)
        if config.job_types:
            # Indeed accepts multiple job types comma-separated
            params["jt"] = ",".join(jt.value for jt in config.job_types)

        # Salary filter (salary parameter)
        if config.salary_min:
            params["salary"] = str(config.salary_min)

        # Remote filter (remotejob or sc parameter)
        if config.remote_option == IndeedRemoteOption.REMOTE:
            params["remotejob"] = "1"
        elif config.remote_option == IndeedRemoteOption.HYBRID:
            params["sc"] = "0kf:attr(DSQF7);"  # Hybrid work attribute

        # Experience level (explvl parameter)
        if config.experience_level:
            params["explvl"] = config.experience_level.value

        # Radius in miles (radius parameter)
        if config.radius_miles is not None:
            params["radius"] = str(config.radius_miles)

        # Company filter
        if config.company:
            params["rbc"] = config.company

        # Sort by date (sort parameter)
        params["sort"] = "date"  # Sort by date for more recent results

        return params

    async def search_jobs(
        self,
        config: IndeedSearchConfig,
    ) -> list[IndeedJobResult]:
        """Search for jobs on Indeed.

        Args:
            config: Search configuration with keywords, filters, etc.

        Returns:
            List of job results matching the search criteria.

        Raises:
            BlockedError: If Indeed blocks the request
            RateLimitExceeded: If rate limit is exceeded
            ScrapingError: If scraping fails
        """
        logger.info(f"Searching Indeed jobs: '{config.keywords}' in {config.location or 'any location'}")

        jobs: list[IndeedJobResult] = []
        start = 0
        page_size = 15  # Indeed returns ~15 results per page
        seen_job_ids: set[str] = set()
        consecutive_empty_pages = 0
        max_empty_pages = 2

        while len(jobs) < config.max_results:
            params = self._build_search_params(config, start)
            url = f"{self.JOBS_SEARCH_URL}?{urlencode(params)}"

            try:
                response = await self._make_request("GET", url)
                html = response.text

                page_jobs = self._parse_job_cards(html)

                if not page_jobs:
                    consecutive_empty_pages += 1
                    if consecutive_empty_pages >= max_empty_pages:
                        logger.info("No more results found")
                        break
                else:
                    consecutive_empty_pages = 0

                # Filter out duplicates
                new_jobs = []
                for job in page_jobs:
                    if job.job_id not in seen_job_ids:
                        seen_job_ids.add(job.job_id)
                        new_jobs.append(job)

                jobs.extend(new_jobs)
                logger.debug(f"Page {start // page_size + 1}: Found {len(new_jobs)} new jobs")

                start += page_size

                # Add extra random delay between pagination requests
                if len(jobs) < config.max_results and page_jobs:
                    await asyncio.sleep(random.uniform(2.0, 5.0))

            except BlockedError:
                logger.warning("Blocked by Indeed, stopping pagination")
                break
            except Exception as e:
                logger.error(f"Error fetching page: {e}")
                break

        # Trim to max_results
        jobs = jobs[: config.max_results]

        logger.info(f"Found {len(jobs)} jobs total")
        return jobs

    def _parse_job_cards(self, html: str) -> list[IndeedJobResult]:
        """Parse job cards from Indeed HTML response.

        Args:
            html: Raw HTML from Indeed

        Returns:
            List of parsed job results
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs: list[IndeedJobResult] = []

        # Indeed uses various selectors for job cards
        job_cards = soup.select(
            "div.job_seen_beacon, "
            "div.jobsearch-SerpJobCard, "
            "div.result, "
            "li.css-5lfssm, "
            "div[data-jk], "
            "td.resultContent"
        )

        # Also try the mosaic format
        if not job_cards:
            job_cards = soup.select("div.mosaic-provider-jobcards div.cardOutline")

        # Try alternative selectors for newer Indeed layout
        if not job_cards:
            job_cards = soup.select("ul.jobsearch-ResultsList > li")

        for card in job_cards:
            try:
                job = self._parse_single_job_card(card)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f"Failed to parse job card: {e}")
                continue

        return jobs

    def _parse_single_job_card(self, card: Tag) -> IndeedJobResult | None:
        """Parse a single job card element.

        Args:
            card: BeautifulSoup Tag element for the job card

        Returns:
            Parsed job result or None if parsing fails
        """
        # Extract job ID from data attribute or link
        job_id = card.get("data-jk")

        if not job_id:
            # Try to find from link
            job_link = card.select_one("a[data-jk], a.jcs-JobTitle")
            if job_link:
                job_id = job_link.get("data-jk") or job_link.get("id", "").replace("job_", "")

        if not job_id:
            # Try from parent
            parent = card.find_parent(attrs={"data-jk": True})
            if parent:
                job_id = parent.get("data-jk")

        if not job_id:
            return None

        # Extract job URL
        job_link = card.select_one(
            "a[data-jk], "
            "a.jcs-JobTitle, "
            "h2.jobTitle a, "
            "a.jobtitle, "
            "a[id^='job_']"
        )
        job_url = ""
        if job_link:
            href = job_link.get("href", "")
            if href:
                job_url = urljoin(self.BASE_URL, href)
            else:
                job_url = f"{self.BASE_URL}/viewjob?jk={job_id}"
        else:
            job_url = f"{self.BASE_URL}/viewjob?jk={job_id}"

        # Extract title
        title_el = card.select_one(
            "h2.jobTitle span[title], "
            "h2.jobTitle a span, "
            "a.jcs-JobTitle span, "
            "a.jobtitle, "
            "h2.jobTitle, "
            "span[title]"
        )
        title = "Unknown Title"
        if title_el:
            title = title_el.get("title") or title_el.get_text(strip=True)

        # Extract company name
        company_el = card.select_one(
            "span.companyName, "
            "span.company, "
            "span[data-testid='company-name'], "
            "a.companyName, "
            "div.companyInfo span.companyName"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown Company"

        # Extract location
        location_el = card.select_one(
            "div.companyLocation, "
            "span.companyLocation, "
            "div[data-testid='text-location'], "
            "span.location, "
            "div.recJobLoc"
        )
        location = location_el.get_text(strip=True) if location_el else None

        # Check for remote
        is_remote = False
        if location:
            is_remote = "remote" in location.lower()

        remote_badge = card.select_one(
            "span.remote, "
            "[data-testid='attribute-snippet-testid']:contains('Remote')"
        )
        if remote_badge:
            is_remote = True

        # Extract salary
        salary_el = card.select_one(
            "div.salary-snippet-container, "
            "span.salaryText, "
            "div[data-testid='attribute-snippet-testid'], "
            "div.metadata.salary-snippet-container, "
            "span.estimated-salary"
        )
        salary_range = None
        if salary_el:
            salary_text = salary_el.get_text(strip=True)
            if "$" in salary_text or "year" in salary_text.lower() or "hour" in salary_text.lower():
                salary_range = salary_text

        # Extract description snippet
        snippet_el = card.select_one(
            "div.job-snippet, "
            "div[data-testid='job-snippet'], "
            "table.jobCardShelfContainer div.job-snippet, "
            "ul.jobCardShelfContainer"
        )
        description_snippet = None
        if snippet_el:
            description_snippet = snippet_el.get_text(separator=" ", strip=True)[:500]

        # Extract posted date
        date_el = card.select_one(
            "span.date, "
            "span[data-testid='myJobsStateDate'], "
            "span.visually-hidden:contains('Posted'), "
            "span.css-qvloho"
        )
        posted_date = None
        if date_el:
            posted_date = date_el.get_text(strip=True)
            # Clean up common prefixes
            posted_date = re.sub(r"^(Posted|Active)\s*", "", posted_date, flags=re.IGNORECASE)

        # Extract employment type from metadata
        employment_type = None
        job_type_el = card.select_one(
            "div.metadata div:contains('Full-time'), "
            "div.metadata div:contains('Part-time'), "
            "div.metadata div:contains('Contract'), "
            "span[data-testid='attribute-snippet-testid']"
        )
        if job_type_el:
            text = job_type_el.get_text(strip=True).lower()
            if "full-time" in text or "full time" in text:
                employment_type = "Full-time"
            elif "part-time" in text or "part time" in text:
                employment_type = "Part-time"
            elif "contract" in text:
                employment_type = "Contract"
            elif "temporary" in text:
                employment_type = "Temporary"
            elif "internship" in text:
                employment_type = "Internship"

        # Extract company rating
        company_rating = None
        rating_el = card.select_one(
            "span.ratingsDisplay, "
            "span[data-testid='holistic-rating'], "
            "span.ratingNumber"
        )
        if rating_el:
            try:
                rating_text = rating_el.get_text(strip=True)
                company_rating = float(re.search(r"[\d.]+", rating_text).group())
            except (AttributeError, ValueError):
                pass

        # Extract review count
        company_review_count = None
        review_el = card.select_one("span.ratingsDisplay + a, a.reviewsCount")
        if review_el:
            try:
                review_text = review_el.get_text(strip=True)
                match = re.search(r"([\d,]+)", review_text)
                if match:
                    company_review_count = int(match.group(1).replace(",", ""))
            except (AttributeError, ValueError):
                pass

        # Check for Easily Apply badge
        easily_apply = bool(
            card.select_one(
                "span.iaLabel, "
                "span:contains('Easily apply'), "
                "span.ialbl"
            )
        )

        # Check for Urgently Hiring badge
        urgently_hiring = bool(
            card.select_one(
                "span:contains('Urgently hiring'), "
                "span.urgentlyHiring"
            )
        )

        # Extract benefits
        benefits: list[str] = []
        benefit_els = card.select(
            "div.jobMetaDataGroup span, "
            "div.metadata ul li"
        )
        for benefit_el in benefit_els[:5]:  # Limit to 5 benefits
            benefit_text = benefit_el.get_text(strip=True)
            if benefit_text and len(benefit_text) < 50:
                benefits.append(benefit_text)

        return IndeedJobResult(
            job_id=str(job_id),
            title=title,
            company=company,
            location=location,
            salary_range=salary_range,
            description_snippet=description_snippet,
            job_url=job_url,
            posted_date=posted_date,
            is_remote=is_remote,
            employment_type=employment_type,
            company_rating=company_rating,
            company_review_count=company_review_count,
            is_easily_apply=easily_apply,
            is_urgently_hiring=urgently_hiring,
            benefits=benefits,
        )

    async def get_job_details(self, job_id: str) -> IndeedJobDetails:
        """Fetch detailed information for a specific job.

        Args:
            job_id: Indeed job ID (jk parameter)

        Returns:
            Detailed job information including full description

        Raises:
            ScrapingError: If fetching details fails
        """
        url = f"{self.BASE_URL}/viewjob?jk={job_id}"

        response = await self._make_request("GET", url)
        html = response.text

        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title_el = soup.select_one(
            "h1.jobsearch-JobInfoHeader-title, "
            "h2.jobTitle, "
            "h1[data-testid='jobsearch-JobInfoHeader-title']"
        )
        title = title_el.get_text(strip=True) if title_el else "Unknown Title"

        # Extract company
        company_el = soup.select_one(
            "div[data-testid='inlineHeader-companyName'], "
            "div.jobsearch-CompanyInfoWithoutHeaderImage a, "
            "div.icl-u-lg-mr--sm a"
        )
        company = company_el.get_text(strip=True) if company_el else "Unknown Company"

        # Extract location
        location_el = soup.select_one(
            "div[data-testid='inlineHeader-companyLocation'], "
            "div.jobsearch-CompanyInfoWithoutHeaderImage div.css-6z8o9s, "
            "div.icl-u-xs-mt--xs"
        )
        location = location_el.get_text(strip=True) if location_el else None

        # Extract salary
        salary_el = soup.select_one(
            "span[data-testid='attribute_snippet_testid'], "
            "div.jobsearch-JobMetadataHeader-item:contains('$'), "
            "div.icl-u-xs-mt--xs span:contains('$')"
        )
        salary_range = None
        if salary_el:
            salary_text = salary_el.get_text(strip=True)
            if "$" in salary_text:
                salary_range = salary_text

        # Extract full description
        description_el = soup.select_one(
            "div#jobDescriptionText, "
            "div.jobsearch-jobDescriptionText, "
            "div[data-testid='job-description']"
        )
        description_full = None
        description_html = None
        if description_el:
            # Clean up scripts and styles
            for element in description_el(["script", "style"]):
                element.decompose()
            description_full = description_el.get_text(separator="\n", strip=True)
            description_html = str(description_el)

        # Check for remote
        is_remote = False
        if location and "remote" in location.lower():
            is_remote = True
        remote_badge = soup.select_one("div:contains('Remote')")
        if remote_badge and "remote" in remote_badge.get_text().lower():
            is_remote = True

        # Extract employment type
        employment_type = None
        job_type_el = soup.select_one(
            "div.jobsearch-JobMetadataHeader-item, "
            "span[data-testid='attribute-snippet-testid']"
        )
        if job_type_el:
            text = job_type_el.get_text(strip=True).lower()
            for jt in ["Full-time", "Part-time", "Contract", "Temporary", "Internship"]:
                if jt.lower() in text:
                    employment_type = jt
                    break

        # Extract posted date
        date_el = soup.select_one(
            "span.css-kyg8or, "
            "span[data-testid='posted-date']"
        )
        posted_date = date_el.get_text(strip=True) if date_el else None

        # Extract qualifications
        qualifications: list[str] = []
        qual_section = soup.select_one("div#qualificationsSection, div.jobsearch-DesktopStickyContainer")
        if qual_section:
            qual_items = qual_section.select("li")
            for item in qual_items[:10]:
                qual_text = item.get_text(strip=True)
                if qual_text:
                    qualifications.append(qual_text)

        # Extract benefits
        benefits: list[str] = []
        benefits_section = soup.select_one("div#benefits, div[data-testid='benefits-container']")
        if benefits_section:
            benefit_items = benefits_section.select("li, div.css-11p7fir")
            for item in benefit_items[:10]:
                benefit_text = item.get_text(strip=True)
                if benefit_text:
                    benefits.append(benefit_text)

        return IndeedJobDetails(
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            salary_range=salary_range,
            job_url=url,
            description_full=description_full,
            description_html=description_html,
            posted_date=posted_date,
            employment_type=employment_type,
            qualifications=qualifications,
            benefits=benefits,
            is_remote=is_remote,
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_rate_limit_status(self) -> RateLimitStatus:
        """Get current rate limit status.

        Returns:
            RateLimitStatus with current token bucket information
        """
        return self.rate_limiter.get_status()

    async def test_connection(self) -> bool:
        """Test connection to Indeed.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(self.BASE_URL, timeout=10.0)
            return response.status_code == 200 and not self._is_captcha_page(response.text)
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# =============================================================================
# Convenience Functions
# =============================================================================


async def search_indeed_jobs(
    keywords: str,
    location: str | None = None,
    salary_min: int | None = None,
    job_types: list[IndeedJobType] | None = None,
    date_posted: IndeedDatePosted = IndeedDatePosted.ANY_TIME,
    remote_option: IndeedRemoteOption = IndeedRemoteOption.ON_SITE,
    max_results: int = 50,
) -> list[IndeedJobResult]:
    """Convenience function to search Indeed jobs.

    Args:
        keywords: Search keywords
        location: Location filter (city, state, or zip)
        salary_min: Minimum salary filter
        job_types: Job type filters
        date_posted: Date posted filter
        remote_option: Remote work filter
        max_results: Maximum results to return

    Returns:
        List of job results
    """
    config = IndeedSearchConfig(
        keywords=keywords,
        location=location,
        salary_min=salary_min,
        job_types=job_types or [],
        date_posted=date_posted,
        remote_option=remote_option,
        max_results=max_results,
    )

    async with IndeedScraper() as scraper:
        return await scraper.search_jobs(config)


async def get_indeed_job_details(job_id: str) -> IndeedJobDetails:
    """Convenience function to get Indeed job details.

    Args:
        job_id: Indeed job ID (jk parameter)

    Returns:
        Detailed job information
    """
    async with IndeedScraper() as scraper:
        return await scraper.get_job_details(job_id)
