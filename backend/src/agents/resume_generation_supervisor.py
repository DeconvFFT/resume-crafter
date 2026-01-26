"""Resume Generation Supervisor for orchestrating multi-agent resume creation.

Coordinates three specialized agents:
1. CollectionAgent - Gathers all user data
2. MappingAgent - Maps and scores content against job requirements
3. ResumeBuilderAgent - Creates ATS-friendly resume output
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import ResumeMatch, User
from src.models.schemas.resume_generation import (
    GeneratedResumeResult,
    ResumeGenerationOptions,
)

from .collection_agent import CollectionAgent
from .mapping_agent import MappingAgent
from .resume_builder_agent import ResumeBuilderAgent

logger = logging.getLogger(__name__)


class ResumeGenerationSupervisor:
    """Orchestrates multi-agent resume generation.

    The supervisor:
    1. Initializes all three specialized agents
    2. Runs them in sequence, passing data between stages
    3. Handles errors and provides fallback behavior
    4. Returns the final generated resume

    Usage:
        supervisor = ResumeGenerationSupervisor(llm_client, db)
        result = await supervisor.generate(user, match, options)
    """

    def __init__(
        self,
        llm_client: Any,
        db: AsyncSession,
    ):
        """Initialize the supervisor with agents.

        Args:
            llm_client: LLM client for agents that need it.
            db: Database session for data queries.
        """
        self._llm = llm_client
        self._db = db

        # Initialize agents
        self._collection_agent = CollectionAgent(db)
        self._mapping_agent = MappingAgent(llm_client)
        self._builder_agent = ResumeBuilderAgent(llm_client)

        logger.info("ResumeGenerationSupervisor initialized with 3 agents")

    async def generate(
        self,
        user: User,
        match: ResumeMatch,
        options: ResumeGenerationOptions | None = None,
    ) -> GeneratedResumeResult:
        """Generate an ATS-friendly resume using multi-agent pipeline.

        Args:
            user: User whose resume to generate.
            match: Resume match containing job context.
            options: Generation configuration (uses defaults if None).

        Returns:
            GeneratedResumeResult with resume content and quality metrics.
        """
        if options is None:
            options = ResumeGenerationOptions()

        logger.info(
            f"Starting resume generation for user {user.id}, "
            f"job {match.job_id}, template={options.template}"
        )

        try:
            # Stage 1: Collection
            logger.info("Stage 1/3: Running CollectionAgent")
            collected = await self._collection_agent.run(user, match)

            logger.info(
                f"CollectionAgent completed: {len(collected.experiences)} experiences, "
                f"{len(collected.projects)} projects, {len(collected.skills)} skills, "
                f"{len(collected.publications)} publications, {len(collected.requirements)} requirements"
            )

            # Stage 2: Mapping
            logger.info("Stage 2/3: Running MappingAgent")
            mapped = await self._mapping_agent.run(collected)

            logger.info(
                f"MappingAgent completed: fit_score={mapped.overall_fit_score:.2f}, "
                f"skill_gaps={len(mapped.skill_gaps)}"
            )

            # Stage 3: Building
            logger.info("Stage 3/3: Running ResumeBuilderAgent")
            result = await self._builder_agent.run(mapped, options)

            logger.info(
                f"ResumeBuilderAgent completed: ats_score={result.ats_score:.0f}, "
                f"exp={result.experiences_included}, proj={result.projects_included}"
            )

            return result

        except Exception as e:
            logger.exception(f"Resume generation failed: {e}")
            # Return a minimal result on error
            return GeneratedResumeResult(
                json_data={"error": str(e)},
                markdown=f"# Error\n\nResume generation failed: {e}",
                ats_score=0.0,
                keyword_density=0.0,
                optimization_notes=[],
            )

    async def generate_json(
        self,
        user: User,
        match: ResumeMatch,
        options: ResumeGenerationOptions | None = None,
    ) -> dict[str, Any]:
        """Generate resume as JSON structure.

        Convenience method that returns just the JSON data.

        Args:
            user: User whose resume to generate.
            match: Resume match containing job context.
            options: Generation configuration.

        Returns:
            JSON-serializable resume dict.
        """
        result = await self.generate(user, match, options)
        return result.json_data

    async def generate_markdown(
        self,
        user: User,
        match: ResumeMatch,
        options: ResumeGenerationOptions | None = None,
    ) -> str:
        """Generate resume as Markdown.

        Convenience method that returns just the markdown.

        Args:
            user: User whose resume to generate.
            match: Resume match containing job context.
            options: Generation configuration.

        Returns:
            Markdown-formatted resume string.
        """
        result = await self.generate(user, match, options)
        return result.markdown


def create_resume_supervisor(
    llm_client: Any,
    db: AsyncSession,
) -> ResumeGenerationSupervisor:
    """Factory function to create a resume generation supervisor.

    Args:
        llm_client: LLM client for agents.
        db: Database session.

    Returns:
        Configured ResumeGenerationSupervisor instance.
    """
    return ResumeGenerationSupervisor(llm_client, db)
