"""Collection Agent for gathering all user data for resume generation.

This agent queries the database to collect all user experiences, projects,
skills, and publications, along with job context for the target position.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.database import (
    Experience,
    JobDescription,
    JobRequirement,
    Project,
    Publication,
    ResumeMatch,
    Skill,
    User,
)
from src.models.schemas.resume_generation import (
    BulletData,
    CollectedResumeData,
    ExperienceData,
    JobRequirementData,
    ProjectData,
    PublicationData,
    SkillData,
)

logger = logging.getLogger(__name__)


class CollectionAgent:
    """Agent that collects all user data for resume generation.

    This agent:
    1. Queries all user experiences with bullets
    2. Queries all user projects with bullets and links
    3. Queries all user skills
    4. Queries all user publications
    5. Queries job description and requirements

    No LLM calls - pure database operations for efficiency.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the collection agent.

        Args:
            db: Database session for queries.
        """
        self._db = db

    async def run(
        self,
        user: User,
        match: ResumeMatch,
    ) -> CollectedResumeData:
        """Collect all user data for resume generation.

        Args:
            user: User whose data to collect.
            match: Resume match containing job context.

        Returns:
            CollectedResumeData with all structured user data.
        """
        logger.info(f"CollectionAgent: Gathering data for user {user.id}")

        # Collect all data in parallel-ish manner
        experiences = await self._collect_experiences(user.id)
        projects = await self._collect_projects(user.id)
        skills = await self._collect_skills(user.id)
        publications = await self._collect_publications(user.id)
        job_data, requirements = await self._collect_job_context(match.job_id)

        # Build profile dict
        profile = {
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "location": user.location,
            "linkedin_url": user.linkedin_url,
            "websites": user.websites or [],
            "summary": user.summary,
        }

        logger.info(
            f"CollectionAgent: Collected {len(experiences)} experiences, "
            f"{len(projects)} projects, {len(skills)} skills, "
            f"{len(publications)} publications, {len(requirements)} requirements"
        )

        return CollectedResumeData(
            profile=profile,
            experiences=experiences,
            projects=projects,
            skills=skills,
            publications=publications,
            job_id=match.job_id,
            job_company=job_data.get("company"),
            job_role=job_data.get("role"),
            job_location=job_data.get("location"),
            requirements=requirements,
        )

    async def _collect_experiences(self, user_id: UUID) -> list[ExperienceData]:
        """Collect all user experiences with bullets."""
        result = await self._db.execute(
            select(Experience)
            .options(selectinload(Experience.bullets))
            .where(
                Experience.user_id == user_id,
                Experience.deleted_at.is_(None),
            )
            .order_by(Experience.start_date.desc())
        )
        experiences = result.scalars().all()

        return [
            ExperienceData(
                id=exp.id,
                company=exp.company,
                role=exp.role,
                location=exp.location,
                start_date=exp.start_date.isoformat() if exp.start_date else None,
                end_date=exp.end_date.isoformat() if exp.end_date else None,
                is_current=exp.is_current,
                bullets=[
                    BulletData(
                        id=bullet.id,
                        content=bullet.content,
                        skills=bullet.skills or [],
                        metrics=bullet.metrics or [],
                        order_index=bullet.order_index,
                    )
                    for bullet in sorted(exp.bullets, key=lambda x: x.order_index)
                    if bullet.deleted_at is None
                ],
            )
            for exp in experiences
        ]

    async def _collect_projects(self, user_id: UUID) -> list[ProjectData]:
        """Collect all user projects with bullets and links."""
        result = await self._db.execute(
            select(Project)
            .options(selectinload(Project.bullets), selectinload(Project.links))
            .where(
                Project.user_id == user_id,
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at.desc())
        )
        projects = result.scalars().all()

        return [
            ProjectData(
                id=proj.id,
                name=proj.name,
                description=proj.description,
                technologies=proj.technologies or [],
                start_date=proj.start_date.isoformat() if proj.start_date else None,
                end_date=proj.end_date.isoformat() if proj.end_date else None,
                bullets=[
                    BulletData(
                        id=bullet.id,
                        content=bullet.content,
                        skills=bullet.skills or [],
                        metrics=bullet.metrics or [],
                        order_index=bullet.order_index,
                    )
                    for bullet in sorted(proj.bullets, key=lambda x: x.order_index)
                    if bullet.deleted_at is None
                ],
                links=[
                    {
                        "url": link.url,
                        "type": link.link_type.value if link.link_type else "other",
                        "title": link.title,
                    }
                    for link in proj.links
                ],
            )
            for proj in projects
        ]

    async def _collect_skills(self, user_id: UUID) -> list[SkillData]:
        """Collect all user skills."""
        result = await self._db.execute(
            select(Skill)
            .where(
                Skill.user_id == user_id,
                Skill.deleted_at.is_(None),
            )
            .order_by(Skill.display_order)
        )
        skills = result.scalars().all()

        return [
            SkillData(
                id=skill.id,
                name=skill.name,
                category=skill.category.value if skill.category else None,
                proficiency=skill.proficiency.value if skill.proficiency else None,
            )
            for skill in skills
        ]

    async def _collect_publications(self, user_id: UUID) -> list[PublicationData]:
        """Collect all user publications."""
        result = await self._db.execute(
            select(Publication)
            .where(
                Publication.user_id == user_id,
                Publication.deleted_at.is_(None),
            )
            .order_by(Publication.display_order)
        )
        publications = result.scalars().all()

        return [
            PublicationData(
                id=pub.id,
                title=pub.title,
                authors=pub.authors,
                venue=pub.venue,
                publication_date=(
                    pub.publication_date.isoformat() if pub.publication_date else None
                ),
                publication_type=(
                    pub.publication_type.value if pub.publication_type else None
                ),
                doi=pub.doi,
                url=pub.url,
            )
            for pub in publications
        ]

    async def _collect_job_context(
        self, job_id: UUID
    ) -> tuple[dict, list[JobRequirementData]]:
        """Collect job description and requirements."""
        # Get job description
        job_result = await self._db.execute(
            select(JobDescription)
            .options(selectinload(JobDescription.requirements))
            .where(JobDescription.id == job_id)
        )
        job = job_result.scalar_one_or_none()

        if not job:
            logger.warning(f"Job {job_id} not found")
            return {}, []

        job_data = {
            "company": job.company,
            "role": job.role,
            "location": job.location,
        }

        requirements = [
            JobRequirementData(
                id=req.id,
                content=req.content,
                requirement_type=req.requirement_type.value if req.requirement_type else "other",
                importance_score=req.importance_score or 3,
                keywords=req.keywords or [],
            )
            for req in job.requirements
        ]

        return job_data, requirements
