"""Supervisor agent for orchestrating specialized extraction agents.

Coordinates the extraction pipeline:
1. Routes to appropriate agents based on document classification
2. Collects and aggregates results
3. Handles errors and fallbacks
"""

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.models.schemas.llm_outputs import (
    DocumentClassification,
    ExperienceExtractionResult,
    ProjectExtractionResult,
    SkillExtractionResult,
    PublicationExtractionResult,
)

from .base import AgentContext, AgentResult, AgentState
from .experience_agent import ExperienceAgent
from .project_agent import ProjectAgent
from .skill_agent import SkillAgent
from .tools.registry import get_default_registry

logger = logging.getLogger(__name__)


@dataclass
class SupervisorResult:
    """Aggregated result from all agents."""

    classification: DocumentClassification | None = None
    experiences: ExperienceExtractionResult | None = None
    projects: ProjectExtractionResult | None = None
    skills: SkillExtractionResult | None = None
    publications: PublicationExtractionResult | None = None

    # Tracking
    agents_run: list[str] = field(default_factory=list)
    tool_calls_made: list[str] = field(default_factory=list)
    total_refinements: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def experience_count(self) -> int:
        return len(self.experiences.experiences) if self.experiences else 0

    @property
    def project_count(self) -> int:
        return len(self.projects.projects) if self.projects else 0

    @property
    def skill_count(self) -> int:
        return len(self.skills.skills) if self.skills else 0

    @property
    def publication_count(self) -> int:
        return len(self.publications.publications) if self.publications else 0


class Supervisor:
    """Orchestrates specialized agents for document processing.

    The supervisor:
    1. Receives a classified document
    2. Determines which agents to run based on classification
    3. Runs agents (potentially in parallel in the future)
    4. Aggregates and returns results

    Usage:
        supervisor = Supervisor(llm_client)
        result = await supervisor.process(
            document_id=doc_id,
            user_id=user_id,
            document_text=text,
            classification=classification,
        )
    """

    def __init__(self, llm_client: Any):
        """Initialize supervisor with agents.

        Args:
            llm_client: LLM client for agent use.
        """
        self._llm = llm_client

        # Initialize specialized agents
        self._experience_agent = ExperienceAgent(llm_client)
        self._project_agent = ProjectAgent(llm_client)
        self._skill_agent = SkillAgent(llm_client)

        # Tool registry for all agents
        self._tool_registry = get_default_registry()

    async def process(
        self,
        document_id: UUID,
        user_id: UUID,
        document_text: str,
        classification: DocumentClassification,
        max_refinements: int = 3,
    ) -> SupervisorResult:
        """Process a document through appropriate agents.

        Args:
            document_id: Document being processed.
            user_id: Owner of the document.
            document_text: Extracted text content.
            classification: Document classification result.
            max_refinements: Max refinement iterations per agent.

        Returns:
            SupervisorResult with all extracted data.
        """
        result = SupervisorResult(classification=classification)

        # Create shared context
        context = AgentContext(
            document_id=document_id,
            user_id=user_id,
            document_text=document_text,
            tool_registry=self._tool_registry,
            max_refinements=max_refinements,
        )

        # Determine which agents to run
        should_run_experiences = (
            classification.classification == "resume" or
            classification.classification == "experience" or
            classification.has_experiences
        )
        should_run_projects = (
            classification.classification == "resume" or
            classification.classification == "project" or
            classification.has_projects
        )
        should_run_skills = True  # Always extract skills
        # Publications use simple extraction (no agent yet)

        logger.info(
            f"Supervisor routing document {document_id}: "
            f"experiences={should_run_experiences}, projects={should_run_projects}, skills={should_run_skills}"
        )

        # Run Experience Agent
        if should_run_experiences:
            logger.info("Running ExperienceAgent")
            exp_result = await self._run_agent(
                self._experience_agent, context, "ExperienceAgent"
            )
            if exp_result.state == AgentState.COMPLETE and exp_result.data:
                result.experiences = exp_result.data
                result.agents_run.append("ExperienceAgent")
                result.tool_calls_made.extend(exp_result.tool_calls_made)
                result.total_refinements += exp_result.refinements_done
            elif exp_result.error:
                result.errors.append(f"ExperienceAgent: {exp_result.error}")

        # Run Project Agent
        if should_run_projects:
            logger.info("Running ProjectAgent")
            # Reset context for new agent
            context.current_refinement = 0
            proj_result = await self._run_agent(
                self._project_agent, context, "ProjectAgent"
            )
            if proj_result.state == AgentState.COMPLETE and proj_result.data:
                result.projects = proj_result.data
                result.agents_run.append("ProjectAgent")
                result.tool_calls_made.extend(proj_result.tool_calls_made)
                result.total_refinements += proj_result.refinements_done
            elif proj_result.error:
                result.errors.append(f"ProjectAgent: {proj_result.error}")

        # Run Skill Agent
        if should_run_skills:
            logger.info("Running SkillAgent")
            context.current_refinement = 0
            skill_result = await self._run_agent(
                self._skill_agent, context, "SkillAgent"
            )
            # Debug logging for skill extraction
            logger.info(
                f"SkillAgent result: state={skill_result.state}, "
                f"data={'set' if skill_result.data else 'None'}, "
                f"data_count={len(skill_result.data.skills) if skill_result.data and hasattr(skill_result.data, 'skills') else 0}, "
                f"error={skill_result.error}"
            )
            if skill_result.state == AgentState.COMPLETE and skill_result.data:
                result.skills = skill_result.data
                result.agents_run.append("SkillAgent")
                result.tool_calls_made.extend(skill_result.tool_calls_made)
                result.total_refinements += skill_result.refinements_done
            elif skill_result.error:
                result.errors.append(f"SkillAgent: {skill_result.error}")

        # Publications - use direct LLM extraction (no agent refinement yet)
        try:
            logger.info("Extracting publications (direct)")
            result.publications = await self._llm.extract_publications(document_text)
            pub_count = len(result.publications.publications) if result.publications and hasattr(result.publications, 'publications') else 0
            logger.info(f"Publications extracted: {pub_count}")
        except Exception as e:
            logger.warning(f"Publication extraction failed: {e}")
            result.errors.append(f"Publications: {e}")

        logger.info(
            f"Supervisor completed: {len(result.agents_run)} agents, "
            f"{len(result.tool_calls_made)} tool calls, "
            f"{result.total_refinements} refinements"
        )

        return result

    async def _run_agent(
        self,
        agent,
        context: AgentContext,
        name: str,
    ) -> AgentResult:
        """Run an agent with error handling."""
        try:
            return await agent.run(context)
        except Exception as e:
            logger.exception(f"Agent {name} failed: {e}")
            return AgentResult(
                state=AgentState.ERROR,
                error=str(e),
            )


# Convenience function for creating supervisor
def create_supervisor(llm_client: Any) -> Supervisor:
    """Create a supervisor with default configuration."""
    return Supervisor(llm_client)
