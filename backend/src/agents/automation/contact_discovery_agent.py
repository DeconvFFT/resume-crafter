"""Contact Discovery Agent for finding hiring managers and recruiters.

This agent:
1. Searches for relevant contacts at target companies
2. Scores contacts by relevance (hiring manager > recruiter > engineer)
3. Extracts contact information
4. Prepares contact data for outreach
"""

import logging
import re
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ContactInfo(BaseModel):
    """Discovered contact information."""
    name: str
    title: str
    company: str
    linkedin_url: str | None = None
    email: str | None = None
    relevance_score: float = Field(ge=0, le=100)
    relevance_reasoning: str | None = None


class ContactDiscoveryResult(BaseModel):
    """Result from contact discovery."""
    company_name: str
    contacts_found: int
    contacts: list[ContactInfo] = Field(default_factory=list)
    search_queries_used: list[str] = Field(default_factory=list)


class ContactDiscoveryAgent:
    """Agent that discovers relevant contacts at target companies.

    Contact relevance scoring:
    - Hiring Manager: 90-100 points
    - Recruiter/Talent: 70-89 points
    - Engineering Manager: 60-79 points
    - Engineer (peer): 40-59 points
    - Other: 20-39 points
    """

    TITLE_SCORES = {
        "hiring manager": 95,
        "head of engineering": 95,
        "engineering director": 92,
        "vp engineering": 90,
        "vp of engineering": 90,
        "director of engineering": 90,
        "technical recruiter": 85,
        "recruiter": 80,
        "talent acquisition": 80,
        "engineering manager": 75,
        "team lead": 70,
        "tech lead": 70,
        "senior engineer": 50,
        "staff engineer": 55,
        "software engineer": 45,
        "engineer": 40,
    }

    def __init__(self, llm_client: Any | None = None):
        """Initialize the contact discovery agent.

        Args:
            llm_client: LLM client for advanced contact analysis.
        """
        self._llm = llm_client

    async def run(
        self,
        company_name: str,
        job_title: str | None = None,
        department: str | None = None,
        max_contacts: int = 10,
    ) -> ContactDiscoveryResult:
        """Discover contacts at a company.

        Args:
            company_name: Name of the target company.
            job_title: Specific job title context for relevance scoring.
            department: Target department (e.g., "Engineering", "Product").
            max_contacts: Maximum number of contacts to return.

        Returns:
            ContactDiscoveryResult with discovered contacts.
        """
        logger.info(f"ContactDiscoveryAgent: Finding contacts at {company_name}")

        # Generate search queries
        queries = self._generate_search_queries(company_name, department)

        # Execute search (mock for now)
        contacts = await self._search_contacts(company_name, queries, max_contacts)

        # Score and rank contacts
        scored_contacts = self._score_contacts(contacts, job_title)

        # Sort by relevance score
        scored_contacts.sort(key=lambda c: c.relevance_score, reverse=True)

        return ContactDiscoveryResult(
            company_name=company_name,
            contacts_found=len(scored_contacts),
            contacts=scored_contacts[:max_contacts],
            search_queries_used=queries,
        )

    async def batch_discover(
        self,
        companies: list[str],
        job_title: str | None = None,
        max_contacts_per_company: int = 5,
    ) -> dict[str, ContactDiscoveryResult]:
        """Discover contacts at multiple companies.

        Args:
            companies: List of company names.
            job_title: Job title context for relevance scoring.
            max_contacts_per_company: Max contacts per company.

        Returns:
            Dict mapping company name to discovery result.
        """
        results = {}
        for company in companies:
            result = await self.run(
                company_name=company,
                job_title=job_title,
                max_contacts=max_contacts_per_company,
            )
            results[company] = result
        return results

    def _generate_search_queries(
        self,
        company: str,
        department: str | None = None,
    ) -> list[str]:
        """Generate LinkedIn search queries."""
        queries = [
            f'"{company}" hiring manager',
            f'"{company}" recruiter',
            f'"{company}" engineering manager',
        ]

        if department:
            queries.append(f'"{company}" "{department}" manager')

        return queries

    async def _search_contacts(
        self,
        company: str,
        queries: list[str],
        max_results: int,
    ) -> list[ContactInfo]:
        """Search for contacts (mock implementation).

        In Phase 6, this will use real LinkedIn scraping.
        """
        # Mock contacts for testing
        mock_contacts = [
            ContactInfo(
                name="Sarah Johnson",
                title="Engineering Manager",
                company=company,
                linkedin_url=f"https://linkedin.com/in/sarah-johnson-{uuid4().hex[:6]}",
                relevance_score=0,  # Will be scored later
            ),
            ContactInfo(
                name="Michael Chen",
                title="Technical Recruiter",
                company=company,
                linkedin_url=f"https://linkedin.com/in/michael-chen-{uuid4().hex[:6]}",
                email=f"michael.chen@{company.lower().replace(' ', '')}.com",
                relevance_score=0,
            ),
            ContactInfo(
                name="Emily Davis",
                title="Head of Engineering",
                company=company,
                linkedin_url=f"https://linkedin.com/in/emily-davis-{uuid4().hex[:6]}",
                relevance_score=0,
            ),
            ContactInfo(
                name="James Wilson",
                title="Senior Software Engineer",
                company=company,
                linkedin_url=f"https://linkedin.com/in/james-wilson-{uuid4().hex[:6]}",
                relevance_score=0,
            ),
            ContactInfo(
                name="Lisa Park",
                title="Talent Acquisition Partner",
                company=company,
                linkedin_url=f"https://linkedin.com/in/lisa-park-{uuid4().hex[:6]}",
                email=f"lisa.park@{company.lower().replace(' ', '')}.com",
                relevance_score=0,
            ),
        ]

        return mock_contacts[:max_results]

    def _score_contacts(
        self,
        contacts: list[ContactInfo],
        job_title: str | None = None,
    ) -> list[ContactInfo]:
        """Score contacts by relevance."""
        scored = []

        for contact in contacts:
            score, reasoning = self._calculate_relevance(contact.title, job_title)
            contact.relevance_score = score
            contact.relevance_reasoning = reasoning
            scored.append(contact)

        return scored

    def _calculate_relevance(
        self,
        contact_title: str,
        job_title: str | None,
    ) -> tuple[float, str]:
        """Calculate relevance score for a contact based on their title."""
        title_lower = contact_title.lower()

        # Check against known title patterns
        for pattern, score in self.TITLE_SCORES.items():
            if pattern in title_lower:
                reasoning = self._get_reasoning(pattern, score)
                return float(score), reasoning

        # Default score for unknown titles
        return 30.0, "Role not directly related to hiring process"

    def _get_reasoning(self, pattern: str, score: float) -> str:
        """Get human-readable reasoning for score."""
        if score >= 90:
            return f"Key decision maker ({pattern})"
        elif score >= 70:
            return f"Directly involved in hiring ({pattern})"
        elif score >= 60:
            return f"Team leadership role ({pattern})"
        elif score >= 40:
            return f"Potential peer connection ({pattern})"
        else:
            return f"Indirect connection ({pattern})"
