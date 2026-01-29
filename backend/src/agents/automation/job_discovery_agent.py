"""Job Discovery Agent for finding jobs across multiple sources.

This agent:
1. Generates boolean search queries from campaign criteria
2. Discovers jobs from multiple sources (LinkedIn, Indeed, Greenhouse, Lever, Glassdoor)
3. Normalizes job data into DiscoveredJob format
4. Handles rate limiting and deduplication
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.config import get_settings
from src.models.database import JobSource, SearchCampaign

# Import all scrapers/clients
from src.integrations.linkedin_scraper import (
    LinkedInScraper,
    LinkedInSearchConfig,
    LinkedInJobResult,
    ExperienceLevel as LinkedInExperienceLevel,
    DatePosted as LinkedInDatePosted,
    AuthenticationError as LinkedInAuthError,
    RateLimitExceeded as LinkedInRateLimit,
    ScrapingError as LinkedInScrapingError,
)
from src.integrations.indeed_scraper import (
    IndeedScraper,
    IndeedSearchConfig,
    IndeedJobResult,
    IndeedJobType,
    IndeedDatePosted,
    IndeedRemoteOption,
    IndeedExperienceLevel,
    IndeedScraperError,
    RateLimitExceeded as IndeedRateLimit,
    BlockedError as IndeedBlockedError,
)
from src.integrations.glassdoor_scraper import (
    GlassdoorScraper,
    GlassdoorSearchConfig,
    GlassdoorJobResult,
    JobType as GlassdoorJobType,
    DatePosted as GlassdoorDatePosted,
    RemoteOption as GlassdoorRemoteOption,
    GlassdoorScraperError,
    RateLimitExceeded as GlassdoorRateLimit,
    BlockedError as GlassdoorBlockedError,
)
from src.integrations.greenhouse_client import (
    GreenhouseClient,
    GreenhouseJob,
    GreenhouseClientError,
)
from src.integrations.lever_client import (
    LeverClient,
    LeverPosting,
    LeverClientError,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class JobSearchQuery(BaseModel):
    """Generated boolean search query for a job source."""
    source: JobSource
    query: str
    location_filter: str | None = None
    salary_filter: str | None = None
    experience_filter: str | None = None
    # For ATS sources (Greenhouse/Lever), store company board tokens
    company_boards: list[str] = Field(default_factory=list)


class DiscoveredJobData(BaseModel):
    """Normalized job data from any source."""
    external_id: str
    source: JobSource
    title: str
    company: str
    location: str | None = None
    description: str | None = None
    requirements: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    url: str
    posted_at: datetime | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)


class JobDiscoveryResult(BaseModel):
    """Result from job discovery run."""
    campaign_id: str
    jobs_found: int
    jobs_new: int
    jobs_duplicate: int
    queries_executed: list[JobSearchQuery]
    errors: list[str] = Field(default_factory=list)
    source_breakdown: dict[str, int] = Field(default_factory=dict)


class JobDiscoveryAgent:
    """Agent that discovers jobs based on search campaign criteria.

    This agent:
    1. Takes a SearchCampaign with targeting criteria
    2. Generates optimized boolean search queries for each source
    3. Executes searches across LinkedIn, Indeed, Glassdoor, Greenhouse, Lever
    4. Normalizes and deduplicates results
    5. Returns DiscoveredJobData for storage
    """

    # Default company boards to search on ATS platforms
    DEFAULT_GREENHOUSE_BOARDS = [
        "spotify", "stripe", "airbnb", "notion", "figma", "vercel",
        "anthropic", "openai", "discord", "dropbox", "instacart"
    ]
    DEFAULT_LEVER_COMPANIES = [
        "netflix", "twitch", "reddit", "cloudflare", "databricks",
        "snowflake", "plaid", "airtable", "linear", "retool"
    ]

    def __init__(
        self,
        llm_client: Any | None = None,
        greenhouse_boards: list[str] | None = None,
        lever_companies: list[str] | None = None,
    ):
        """Initialize the job discovery agent.

        Args:
            llm_client: LLM client for generating search queries.
            greenhouse_boards: List of Greenhouse board tokens to search.
            lever_companies: List of Lever company slugs to search.
        """
        self._llm = llm_client
        self._rate_limit_delay = 2.0  # seconds between requests
        self._greenhouse_boards = greenhouse_boards or self.DEFAULT_GREENHOUSE_BOARDS
        self._lever_companies = lever_companies or self.DEFAULT_LEVER_COMPANIES

    async def run(
        self,
        campaign: SearchCampaign,
        sources: list[JobSource] | None = None,
        max_jobs_per_source: int = 50,
    ) -> tuple[list[DiscoveredJobData], JobDiscoveryResult]:
        """Discover jobs for a campaign from all configured sources.

        Args:
            campaign: Search campaign with targeting criteria.
            sources: Specific sources to search (default: all enabled).
            max_jobs_per_source: Maximum jobs to fetch per source.

        Returns:
            Tuple of (discovered jobs, discovery result summary).
        """
        logger.info(f"JobDiscoveryAgent: Starting discovery for campaign {campaign.id}")

        # Default to all major sources
        if sources is None:
            sources = [
                JobSource.LINKEDIN,
                JobSource.INDEED,
                JobSource.GLASSDOOR,
                JobSource.GREENHOUSE,
                JobSource.LEVER,
            ]

        # Generate search queries for each source
        queries = await self._generate_search_queries(campaign, sources)

        # Execute searches in parallel for efficiency
        all_jobs: list[DiscoveredJobData] = []
        errors: list[str] = []
        source_breakdown: dict[str, int] = {}

        # Run searches concurrently
        tasks = []
        for query in queries:
            tasks.append(self._execute_search_safe(query, max_jobs_per_source))

        results = await asyncio.gather(*tasks)

        for query, (jobs, error) in zip(queries, results):
            if error:
                errors.append(f"{query.source.value}: {error}")
            if jobs:
                all_jobs.extend(jobs)
                source_breakdown[query.source.value] = len(jobs)

        # Deduplicate by external_id + source
        unique_jobs, duplicates = self._deduplicate_jobs(all_jobs)

        result = JobDiscoveryResult(
            campaign_id=str(campaign.id),
            jobs_found=len(all_jobs),
            jobs_new=len(unique_jobs),
            jobs_duplicate=duplicates,
            queries_executed=queries,
            errors=errors,
            source_breakdown=source_breakdown,
        )

        logger.info(
            f"JobDiscoveryAgent: Found {result.jobs_new} new jobs across {len(source_breakdown)} sources. "
            f"Breakdown: {source_breakdown}"
        )
        return unique_jobs, result

    async def _execute_search_safe(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> tuple[list[DiscoveredJobData], str | None]:
        """Execute search with error handling.

        Returns:
            Tuple of (jobs, error_message). Error is None on success.
        """
        try:
            jobs = await self._execute_search(query, max_results)
            return jobs, None
        except Exception as e:
            logger.error(f"Error searching {query.source}: {e}")
            return [], str(e)

    async def _generate_search_queries(
        self,
        campaign: SearchCampaign,
        sources: list[JobSource],
    ) -> list[JobSearchQuery]:
        """Generate optimized boolean search queries from campaign criteria."""
        queries = []

        for source in sources:
            query = self._build_query_for_source(campaign, source)
            queries.append(query)

        return queries

    def _build_query_for_source(
        self,
        campaign: SearchCampaign,
        source: JobSource,
    ) -> JobSearchQuery:
        """Build a search query optimized for a specific source."""
        # Build boolean query from target roles and keywords
        role_terms = " OR ".join(f'"{role}"' for role in campaign.target_roles)

        keyword_terms = ""
        if campaign.keywords:
            keyword_terms = " AND (" + " OR ".join(campaign.keywords) + ")"

        exclude_terms = ""
        if campaign.excluded_keywords:
            exclude_terms = " NOT (" + " OR ".join(campaign.excluded_keywords) + ")"

        query = f"({role_terms}){keyword_terms}{exclude_terms}"

        # Location filter
        location_filter = None
        if campaign.target_locations:
            location_filter = " OR ".join(campaign.target_locations)

        # For ATS platforms, include company boards
        company_boards = []
        if source == JobSource.GREENHOUSE:
            company_boards = self._greenhouse_boards
        elif source == JobSource.LEVER:
            company_boards = self._lever_companies

        return JobSearchQuery(
            source=source,
            query=query,
            location_filter=location_filter,
            experience_filter=campaign.experience_level if campaign.experience_level != "any" else None,
            company_boards=company_boards,
        )

    async def _execute_search(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> list[DiscoveredJobData]:
        """Execute search on a source using real integrations.

        Args:
            query: Search query configuration.
            max_results: Maximum jobs to fetch.

        Returns:
            List of discovered jobs.
        """
        logger.info(f"Executing search on {query.source}: {query.query[:50]}...")

        if query.source == JobSource.LINKEDIN:
            return await self._search_linkedin(query, max_results)
        elif query.source == JobSource.INDEED:
            return await self._search_indeed(query, max_results)
        elif query.source == JobSource.GLASSDOOR:
            return await self._search_glassdoor(query, max_results)
        elif query.source == JobSource.GREENHOUSE:
            return await self._search_greenhouse(query, max_results)
        elif query.source == JobSource.LEVER:
            return await self._search_lever(query, max_results)
        else:
            logger.warning(f"Unsupported job source: {query.source}")
            return []

    # =========================================================================
    # LinkedIn Integration
    # =========================================================================

    async def _search_linkedin(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> list[DiscoveredJobData]:
        """Search for jobs on LinkedIn."""
        if not settings.linkedin_session_cookie:
            logger.warning("LinkedIn session cookie not configured, skipping LinkedIn search")
            return []

        config = self._build_linkedin_config(query, max_results)

        try:
            async with LinkedInScraper(
                session_cookie=settings.linkedin_session_cookie
            ) as scraper:
                linkedin_jobs = await scraper.search_jobs(config)
                return [self._convert_linkedin_job(job, query) for job in linkedin_jobs]

        except (LinkedInAuthError, LinkedInRateLimit, LinkedInScrapingError) as e:
            logger.error(f"LinkedIn search failed: {e}")
            raise

    def _build_linkedin_config(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> LinkedInSearchConfig:
        """Build LinkedInSearchConfig from JobSearchQuery."""
        # Extract keywords from boolean query
        quoted_terms = re.findall(r'"([^"]+)"', query.query)
        keywords = " ".join(quoted_terms[:3]) if quoted_terms else query.query

        # Map experience level
        experience_levels = []
        if query.experience_filter:
            exp_map = {
                "entry": [LinkedInExperienceLevel.ENTRY_LEVEL, LinkedInExperienceLevel.ASSOCIATE],
                "mid": [LinkedInExperienceLevel.MID_SENIOR],
                "senior": [LinkedInExperienceLevel.MID_SENIOR, LinkedInExperienceLevel.DIRECTOR],
                "executive": [LinkedInExperienceLevel.DIRECTOR, LinkedInExperienceLevel.EXECUTIVE],
            }
            experience_levels = exp_map.get(query.experience_filter.lower(), [])

        # Extract first location
        location = None
        if query.location_filter:
            locations = query.location_filter.split(" OR ")
            location = locations[0].strip() if locations else None

        return LinkedInSearchConfig(
            keywords=keywords,
            location=location,
            experience_levels=experience_levels,
            date_posted=LinkedInDatePosted.PAST_WEEK,
            max_results=min(max_results, 50),
        )

    def _convert_linkedin_job(
        self,
        job: LinkedInJobResult,
        query: JobSearchQuery,
    ) -> DiscoveredJobData:
        """Convert LinkedIn job to DiscoveredJobData."""
        salary_min, salary_max = self._parse_salary(job.salary_range)
        posted_at = self._parse_relative_date(job.posted_date)

        return DiscoveredJobData(
            external_id=job.job_id,
            source=JobSource.LINKEDIN,
            title=job.title,
            company=job.company,
            location=job.location or ("Remote" if job.is_remote else "Unknown"),
            description=job.description_snippet,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency="USD" if (salary_min or salary_max) else None,
            url=job.job_url,
            posted_at=posted_at,
            raw_data={
                "company_id": job.company_id,
                "is_easy_apply": job.is_easy_apply,
                "is_remote": job.is_remote,
                "employment_type": job.employment_type,
                "seniority_level": job.seniority_level,
                "query": query.query,
            },
        )

    # =========================================================================
    # Indeed Integration
    # =========================================================================

    async def _search_indeed(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> list[DiscoveredJobData]:
        """Search for jobs on Indeed."""
        config = self._build_indeed_config(query, max_results)

        try:
            async with IndeedScraper() as scraper:
                indeed_jobs = await scraper.search_jobs(config)
                return [self._convert_indeed_job(job, query) for job in indeed_jobs]

        except (IndeedScraperError, IndeedRateLimit, IndeedBlockedError) as e:
            logger.error(f"Indeed search failed: {e}")
            raise

    def _build_indeed_config(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> IndeedSearchConfig:
        """Build IndeedSearchConfig from JobSearchQuery."""
        # Extract keywords
        quoted_terms = re.findall(r'"([^"]+)"', query.query)
        keywords = " ".join(quoted_terms[:3]) if quoted_terms else query.query

        # Extract location
        location = None
        if query.location_filter:
            locations = query.location_filter.split(" OR ")
            location = locations[0].strip() if locations else None

        # Map experience level
        experience_level = None
        if query.experience_filter:
            exp_map = {
                "entry": IndeedExperienceLevel.ENTRY,
                "mid": IndeedExperienceLevel.MID,
                "senior": IndeedExperienceLevel.SENIOR,
            }
            experience_level = exp_map.get(query.experience_filter.lower())

        return IndeedSearchConfig(
            keywords=keywords,
            location=location,
            date_posted=IndeedDatePosted.LAST_7_DAYS,
            experience_level=experience_level,
            max_results=min(max_results, 100),
        )

    def _convert_indeed_job(
        self,
        job: IndeedJobResult,
        query: JobSearchQuery,
    ) -> DiscoveredJobData:
        """Convert Indeed job to DiscoveredJobData."""
        salary_min, salary_max = self._parse_salary(job.salary_range)
        posted_at = self._parse_relative_date(job.posted_date)

        return DiscoveredJobData(
            external_id=job.job_id,
            source=JobSource.INDEED,
            title=job.title,
            company=job.company,
            location=job.location or ("Remote" if job.is_remote else "Unknown"),
            description=job.description_snippet,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency="USD" if (salary_min or salary_max) else None,
            url=job.job_url,
            posted_at=posted_at,
            raw_data={
                "is_remote": job.is_remote,
                "employment_type": job.employment_type,
                "is_easily_apply": job.is_easily_apply,
                "company_rating": job.company_rating,
                "query": query.query,
            },
        )

    # =========================================================================
    # Glassdoor Integration
    # =========================================================================

    async def _search_glassdoor(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> list[DiscoveredJobData]:
        """Search for jobs on Glassdoor."""
        config = self._build_glassdoor_config(query, max_results)

        try:
            async with GlassdoorScraper() as scraper:
                glassdoor_jobs = await scraper.search_jobs(config)
                return [self._convert_glassdoor_job(job, query) for job in glassdoor_jobs]

        except (GlassdoorScraperError, GlassdoorRateLimit, GlassdoorBlockedError) as e:
            logger.error(f"Glassdoor search failed: {e}")
            raise

    def _build_glassdoor_config(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> GlassdoorSearchConfig:
        """Build GlassdoorSearchConfig from JobSearchQuery."""
        # Extract keywords
        quoted_terms = re.findall(r'"([^"]+)"', query.query)
        keywords = " ".join(quoted_terms[:3]) if quoted_terms else query.query

        # Extract location
        location = None
        if query.location_filter:
            locations = query.location_filter.split(" OR ")
            location = locations[0].strip() if locations else None

        return GlassdoorSearchConfig(
            keywords=keywords,
            location=location,
            date_posted=GlassdoorDatePosted.LAST_WEEK,
            max_results=min(max_results, 100),
        )

    def _convert_glassdoor_job(
        self,
        job: GlassdoorJobResult,
        query: JobSearchQuery,
    ) -> DiscoveredJobData:
        """Convert Glassdoor job to DiscoveredJobData."""
        salary_min, salary_max = self._parse_salary(job.salary_range)
        posted_at = self._parse_relative_date(job.posted_date)

        return DiscoveredJobData(
            external_id=job.job_id,
            source=JobSource.GLASSDOOR,
            title=job.title,
            company=job.company,
            location=job.location or ("Remote" if job.is_remote else "Unknown"),
            description=job.description_snippet,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency="USD" if (salary_min or salary_max) else None,
            url=job.job_url,
            posted_at=posted_at,
            raw_data={
                "company_rating": job.company_rating,
                "is_remote": job.is_remote,
                "employment_type": job.employment_type,
                "easy_apply": job.easy_apply,
                "query": query.query,
            },
        )

    # =========================================================================
    # Greenhouse Integration (ATS API)
    # =========================================================================

    async def _search_greenhouse(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> list[DiscoveredJobData]:
        """Search for jobs on Greenhouse company boards."""
        if not query.company_boards:
            logger.warning("No Greenhouse boards configured")
            return []

        all_jobs: list[DiscoveredJobData] = []

        # Extract search keywords for filtering
        quoted_terms = re.findall(r'"([^"]+)"', query.query)
        search_terms = [t.lower() for t in quoted_terms] if quoted_terms else []

        try:
            async with GreenhouseClient() as client:
                # Fetch from all configured boards
                jobs_by_board = await client.get_jobs_from_boards(query.company_boards)

                for board_token, jobs in jobs_by_board.items():
                    for job in jobs:
                        # Filter by search terms if we have them
                        if search_terms:
                            title_lower = job.title.lower()
                            if not any(term in title_lower for term in search_terms):
                                continue

                        converted = self._convert_greenhouse_job(job, query, board_token)
                        all_jobs.append(converted)

                        if len(all_jobs) >= max_results:
                            break

                    if len(all_jobs) >= max_results:
                        break

        except GreenhouseClientError as e:
            logger.error(f"Greenhouse search failed: {e}")
            raise

        return all_jobs[:max_results]

    def _convert_greenhouse_job(
        self,
        job: GreenhouseJob,
        query: JobSearchQuery,
        board_token: str,
    ) -> DiscoveredJobData:
        """Convert Greenhouse job to DiscoveredJobData."""
        # Parse location
        location = None
        if job.location:
            location = job.location.name

        # Parse posted date
        posted_at = None
        if job.updated_at:
            try:
                posted_at = datetime.fromisoformat(job.updated_at.replace("Z", "+00:00"))
            except ValueError:
                pass

        return DiscoveredJobData(
            external_id=str(job.id),
            source=JobSource.GREENHOUSE,
            title=job.title,
            company=board_token.replace("-", " ").title(),  # Convert board token to company name
            location=location,
            description=job.content[:500] if job.content else None,
            url=job.absolute_url,
            posted_at=posted_at,
            raw_data={
                "board_token": board_token,
                "departments": [d.name for d in job.departments] if job.departments else [],
                "offices": [o.name for o in job.offices] if job.offices else [],
                "internal_job_id": job.internal_job_id,
                "query": query.query,
            },
        )

    # =========================================================================
    # Lever Integration (ATS API)
    # =========================================================================

    async def _search_lever(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> list[DiscoveredJobData]:
        """Search for jobs on Lever company postings."""
        if not query.company_boards:
            logger.warning("No Lever companies configured")
            return []

        all_jobs: list[DiscoveredJobData] = []

        # Extract search keywords for filtering
        quoted_terms = re.findall(r'"([^"]+)"', query.query)
        search_terms = [t.lower() for t in quoted_terms] if quoted_terms else []

        try:
            async with LeverClient() as client:
                # Fetch from all configured companies
                postings_by_company = await client.get_postings_from_companies(query.company_boards)

                for company, postings in postings_by_company.items():
                    for posting in postings:
                        # Filter by search terms if we have them
                        if search_terms:
                            title_lower = posting.text.lower()
                            if not any(term in title_lower for term in search_terms):
                                continue

                        converted = self._convert_lever_job(posting, query, company)
                        all_jobs.append(converted)

                        if len(all_jobs) >= max_results:
                            break

                    if len(all_jobs) >= max_results:
                        break

        except LeverClientError as e:
            logger.error(f"Lever search failed: {e}")
            raise

        return all_jobs[:max_results]

    def _convert_lever_job(
        self,
        posting: LeverPosting,
        query: JobSearchQuery,
        company: str,
    ) -> DiscoveredJobData:
        """Convert Lever posting to DiscoveredJobData."""
        # Parse location from categories
        location = None
        if posting.categories:
            location = posting.categories.location

        # Parse posted date
        posted_at = None
        if posting.createdAt:
            try:
                # Lever uses milliseconds timestamp
                posted_at = datetime.fromtimestamp(posting.createdAt / 1000)
            except (ValueError, TypeError):
                pass

        # Get description from content blocks
        description = None
        if posting.lists:
            for block in posting.lists:
                if block.text.lower() in ["description", "about the role", "overview"]:
                    description = block.content[:500] if block.content else None
                    break

        return DiscoveredJobData(
            external_id=posting.id,
            source=JobSource.LEVER,
            title=posting.text,
            company=company.replace("-", " ").title(),
            location=location,
            description=description,
            url=posting.hostedUrl,
            posted_at=posted_at,
            raw_data={
                "company_slug": company,
                "team": posting.categories.team if posting.categories else None,
                "department": posting.categories.department if posting.categories else None,
                "commitment": posting.categories.commitment if posting.categories else None,
                "apply_url": posting.applyUrl,
                "query": query.query,
            },
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _parse_salary(self, salary_str: str | None) -> tuple[int | None, int | None]:
        """Parse salary range from string like '$120K - $180K' or '$120,000 - $180,000'."""
        if not salary_str:
            return None, None

        salary_min = None
        salary_max = None

        matches = re.findall(r'\$?([\d,]+)K?', salary_str, re.IGNORECASE)
        if len(matches) >= 1:
            salary_str_clean = matches[0].replace(',', '')
            salary_min = int(salary_str_clean)
            if salary_min < 1000:  # Likely in thousands (e.g., 120K)
                salary_min *= 1000
        if len(matches) >= 2:
            salary_str_clean = matches[1].replace(',', '')
            salary_max = int(salary_str_clean)
            if salary_max < 1000:
                salary_max *= 1000

        return salary_min, salary_max

    def _parse_relative_date(self, date_str: str | None) -> datetime | None:
        """Parse relative date like '2 days ago' or '1 week ago'."""
        if not date_str:
            return None

        now = datetime.utcnow()
        date_lower = date_str.lower()

        match = re.search(r'(\d+)', date_lower)
        num = int(match.group(1)) if match else 1

        if "hour" in date_lower:
            return now - timedelta(hours=num)
        elif "day" in date_lower:
            return now - timedelta(days=num)
        elif "week" in date_lower:
            return now - timedelta(weeks=num)
        elif "month" in date_lower:
            return now - timedelta(days=num * 30)
        elif "just" in date_lower or "today" in date_lower:
            return now

        return now  # Default to now if can't parse

    def _deduplicate_jobs(
        self,
        jobs: list[DiscoveredJobData],
    ) -> tuple[list[DiscoveredJobData], int]:
        """Remove duplicate jobs based on external_id + source."""
        seen = set()
        unique = []
        duplicates = 0

        for job in jobs:
            key = (job.external_id, job.source)
            if key not in seen:
                seen.add(key)
                unique.append(job)
            else:
                duplicates += 1

        return unique, duplicates
