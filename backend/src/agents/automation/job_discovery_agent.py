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

from src.models.database import JobSource, DiscoveredJob, SearchCampaign

logger = logging.getLogger(__name__)


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
        """Execute search on a source (mock implementation).

        In Phase 6, this will be replaced with real scraping integrations.
        """
        # Mock implementation - returns sample jobs
        logger.info(f"Executing search on {query.source}: {query.query[:50]}...")

        # Generate mock jobs for testing
        mock_jobs = self._generate_mock_jobs(query, min(max_results, 5))
        return mock_jobs

    def _generate_mock_jobs(
        self,
        query: JobSearchQuery,
        count: int,
    ) -> list[DiscoveredJobData]:
        """Generate mock job data for testing."""
        mock_companies = ["TechCorp", "AI Labs", "DataFlow", "CloudScale", "InnovateTech"]
        mock_titles = ["Software Engineer", "ML Engineer", "Data Scientist", "Backend Developer", "Full Stack Engineer"]

        jobs = []
        for i in range(count):
            job = DiscoveredJobData(
                external_id=f"{query.source.value}_{uuid4().hex[:8]}",
                source=query.source,
                title=mock_titles[i % len(mock_titles)],
                company=mock_companies[i % len(mock_companies)],
                location=query.location_filter.split(" OR ")[0] if query.location_filter else "Remote",
                description=f"We are looking for a talented {mock_titles[i % len(mock_titles)]} to join our team...",
                requirements="5+ years experience, Python, Machine Learning, Cloud platforms",
                salary_min=120000 + (i * 10000),
                salary_max=180000 + (i * 10000),
                salary_currency="USD",
                url=f"https://{query.source.value}.com/jobs/{uuid4().hex[:8]}",
                posted_at=datetime.utcnow(),
                raw_data={"query": query.query, "source": query.source.value},
            )
            jobs.append(job)

        return jobs

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
