"""Job Discovery Agent for finding jobs across multiple sources.

This agent:
1. Generates boolean search queries from campaign criteria
2. Discovers jobs from multiple sources (LinkedIn, Indeed, Greenhouse, etc.)
3. Normalizes job data into DiscoveredJob format
4. Handles rate limiting and deduplication
"""

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.config import get_settings
from src.models.database import JobSource, DiscoveredJob, SearchCampaign
from src.integrations.linkedin_scraper import (
    LinkedInScraper,
    LinkedInSearchConfig,
    LinkedInJobResult,
    ExperienceLevel,
    DatePosted,
    RemoteOption,
    AuthenticationError,
    RateLimitExceeded,
    ScrapingError,
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


class JobDiscoveryAgent:
    """Agent that discovers jobs based on search campaign criteria.

    This agent:
    1. Takes a SearchCampaign with targeting criteria
    2. Generates optimized boolean search queries for each source
    3. Executes searches (mock for now, real scraping in integrations phase)
    4. Normalizes and deduplicates results
    5. Returns DiscoveredJobData for storage
    """

    def __init__(self, llm_client: Any | None = None):
        """Initialize the job discovery agent.

        Args:
            llm_client: LLM client for generating search queries.
        """
        self._llm = llm_client
        self._rate_limit_delay = 2.0  # seconds between requests

    async def run(
        self,
        campaign: SearchCampaign,
        sources: list[JobSource] | None = None,
        max_jobs_per_source: int = 50,
    ) -> tuple[list[DiscoveredJobData], JobDiscoveryResult]:
        """Discover jobs for a campaign.

        Args:
            campaign: Search campaign with targeting criteria.
            sources: Specific sources to search (default: all enabled).
            max_jobs_per_source: Maximum jobs to fetch per source.

        Returns:
            Tuple of (discovered jobs, discovery result summary).
        """
        logger.info(f"JobDiscoveryAgent: Starting discovery for campaign {campaign.id}")

        # Default to all sources if not specified
        if sources is None:
            sources = [JobSource.LINKEDIN, JobSource.INDEED, JobSource.GREENHOUSE]

        # Generate search queries for each source
        queries = await self._generate_search_queries(campaign, sources)

        # Execute searches and collect jobs
        all_jobs: list[DiscoveredJobData] = []
        errors: list[str] = []

        for query in queries:
            try:
                jobs = await self._execute_search(query, max_jobs_per_source)
                all_jobs.extend(jobs)
                await asyncio.sleep(self._rate_limit_delay)
            except Exception as e:
                logger.error(f"Error searching {query.source}: {e}")
                errors.append(f"{query.source}: {str(e)}")

        # Deduplicate by external_id + source
        unique_jobs, duplicates = self._deduplicate_jobs(all_jobs)

        result = JobDiscoveryResult(
            campaign_id=str(campaign.id),
            jobs_found=len(all_jobs),
            jobs_new=len(unique_jobs),
            jobs_duplicate=duplicates,
            queries_executed=queries,
            errors=errors,
        )

        logger.info(f"JobDiscoveryAgent: Found {result.jobs_new} new jobs")
        return unique_jobs, result

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

        return JobSearchQuery(
            source=source,
            query=query,
            location_filter=location_filter,
            experience_filter=campaign.experience_level if campaign.experience_level != "any" else None,
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
            # Indeed scraping not yet implemented
            logger.warning("Indeed scraping not yet implemented, skipping")
            return []
        elif query.source == JobSource.GREENHOUSE:
            # Greenhouse API not yet implemented
            logger.warning("Greenhouse API not yet implemented, skipping")
            return []
        else:
            logger.warning(f"Unknown job source: {query.source}")
            return []

    async def _search_linkedin(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> list[DiscoveredJobData]:
        """Search for jobs on LinkedIn using the real scraper.

        Args:
            query: Search query configuration.
            max_results: Maximum jobs to fetch.

        Returns:
            List of discovered jobs from LinkedIn.
        """
        # Check if LinkedIn session cookie is configured
        if not settings.linkedin_session_cookie:
            logger.error(
                "LinkedIn session cookie not configured. "
                "Set LINKEDIN_SESSION_COOKIE in environment variables."
            )
            raise ScrapingError(
                "LinkedIn session cookie not configured. "
                "Please set LINKEDIN_SESSION_COOKIE environment variable."
            )

        # Build LinkedIn search config from query
        config = self._build_linkedin_config(query, max_results)

        # Execute search using LinkedIn scraper
        try:
            async with LinkedInScraper(
                session_cookie=settings.linkedin_session_cookie
            ) as scraper:
                linkedin_jobs = await scraper.search_jobs(config)

                # Convert to DiscoveredJobData format
                jobs = []
                for lj in linkedin_jobs:
                    job = self._convert_linkedin_job(lj, query)
                    jobs.append(job)

                logger.info(f"LinkedIn search found {len(jobs)} jobs")
                return jobs

        except AuthenticationError as e:
            logger.error(f"LinkedIn authentication failed: {e}")
            raise ScrapingError(f"LinkedIn authentication failed: {e}")
        except RateLimitExceeded as e:
            logger.warning(f"LinkedIn rate limit exceeded: {e}")
            raise ScrapingError(f"LinkedIn rate limit exceeded: {e}")
        except Exception as e:
            logger.error(f"LinkedIn search failed: {e}")
            raise ScrapingError(f"LinkedIn search failed: {e}")

    def _build_linkedin_config(
        self,
        query: JobSearchQuery,
        max_results: int,
    ) -> LinkedInSearchConfig:
        """Build LinkedInSearchConfig from JobSearchQuery.

        Args:
            query: Our internal query format.
            max_results: Maximum jobs to fetch.

        Returns:
            LinkedIn-specific search configuration.
        """
        # Extract keywords from boolean query
        # The query is in format: ("role1" OR "role2") AND (keyword1 OR keyword2) NOT (excluded)
        # We'll simplify by using the first role term as keywords
        keywords = query.query
        # Try to extract quoted terms
        import re
        quoted_terms = re.findall(r'"([^"]+)"', query.query)
        if quoted_terms:
            keywords = " ".join(quoted_terms[:3])  # Use up to 3 terms

        # Map experience level filter
        experience_levels = []
        if query.experience_filter:
            exp_map = {
                "entry": [ExperienceLevel.ENTRY_LEVEL, ExperienceLevel.ASSOCIATE],
                "mid": [ExperienceLevel.MID_SENIOR],
                "senior": [ExperienceLevel.MID_SENIOR, ExperienceLevel.DIRECTOR],
                "executive": [ExperienceLevel.DIRECTOR, ExperienceLevel.EXECUTIVE],
            }
            experience_levels = exp_map.get(query.experience_filter.lower(), [])

        # Extract first location if multiple
        location = None
        if query.location_filter:
            locations = query.location_filter.split(" OR ")
            location = locations[0].strip() if locations else None

        return LinkedInSearchConfig(
            keywords=keywords,
            location=location,
            experience_levels=experience_levels,
            date_posted=DatePosted.PAST_WEEK,  # Focus on recent jobs
            remote_options=[],  # Include all remote options
            max_results=min(max_results, 50),  # LinkedIn max per search
        )

    def _convert_linkedin_job(
        self,
        linkedin_job: LinkedInJobResult,
        query: JobSearchQuery,
    ) -> DiscoveredJobData:
        """Convert LinkedIn job result to our internal format.

        Args:
            linkedin_job: Job from LinkedIn scraper.
            query: Original search query for metadata.

        Returns:
            Normalized DiscoveredJobData.
        """
        # Parse salary range if available
        salary_min = None
        salary_max = None
        if linkedin_job.salary_range:
            # Try to parse salary like "$120K - $180K" or "$120,000 - $180,000"
            import re
            salary_matches = re.findall(r'\$?([\d,]+)K?', linkedin_job.salary_range)
            if len(salary_matches) >= 1:
                salary_str = salary_matches[0].replace(',', '')
                salary_min = int(salary_str)
                if salary_min < 1000:  # Likely in thousands (e.g., 120K)
                    salary_min *= 1000
            if len(salary_matches) >= 2:
                salary_str = salary_matches[1].replace(',', '')
                salary_max = int(salary_str)
                if salary_max < 1000:
                    salary_max *= 1000

        # Parse posted date if available
        posted_at = None
        if linkedin_job.posted_date:
            # LinkedIn uses relative dates like "2 days ago", "1 week ago"
            from datetime import timedelta
            now = datetime.utcnow()
            posted_str = linkedin_job.posted_date.lower()
            if "hour" in posted_str:
                hours = int(re.search(r'(\d+)', posted_str).group(1)) if re.search(r'(\d+)', posted_str) else 1
                posted_at = now - timedelta(hours=hours)
            elif "day" in posted_str:
                days = int(re.search(r'(\d+)', posted_str).group(1)) if re.search(r'(\d+)', posted_str) else 1
                posted_at = now - timedelta(days=days)
            elif "week" in posted_str:
                weeks = int(re.search(r'(\d+)', posted_str).group(1)) if re.search(r'(\d+)', posted_str) else 1
                posted_at = now - timedelta(weeks=weeks)
            elif "month" in posted_str:
                months = int(re.search(r'(\d+)', posted_str).group(1)) if re.search(r'(\d+)', posted_str) else 1
                posted_at = now - timedelta(days=months * 30)
            else:
                posted_at = now  # Default to now if can't parse

        return DiscoveredJobData(
            external_id=linkedin_job.job_id,
            source=JobSource.LINKEDIN,
            title=linkedin_job.title,
            company=linkedin_job.company,
            location=linkedin_job.location or ("Remote" if linkedin_job.is_remote else "Unknown"),
            description=linkedin_job.description_snippet,
            requirements=None,  # Would need to fetch full job details
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency="USD" if (salary_min or salary_max) else None,
            url=linkedin_job.job_url,
            posted_at=posted_at,
            raw_data={
                "company_id": linkedin_job.company_id,
                "company_logo_url": linkedin_job.company_logo_url,
                "applicant_count": linkedin_job.applicant_count,
                "is_easy_apply": linkedin_job.is_easy_apply,
                "is_remote": linkedin_job.is_remote,
                "employment_type": linkedin_job.employment_type,
                "seniority_level": linkedin_job.seniority_level,
                "query": query.query,
            },
        )

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
