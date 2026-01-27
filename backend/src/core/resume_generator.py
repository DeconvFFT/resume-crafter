"""Resume generation in multiple formats.

Supports both simple generation (direct database queries) and
multi-agent optimized generation (CollectionAgent -> MappingAgent -> ResumeBuilderAgent).
"""

import logging
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.database import (
    Experience,
    ExperienceBullet,
    Project,
    ProjectBullet,
    Publication,
    ResumeMatch,
    ResumeMatchItem,
    Skill,
    User,
)

logger = logging.getLogger(__name__)


class ResumeGenerator:
    """Generate resumes in various formats from match results."""

    async def generate_json(
        self,
        db: AsyncSession,
        match: ResumeMatch,
        user: User,
    ) -> dict[str, Any]:
        """Generate resume as JSON structure.

        Args:
            db: Database session.
            match: Resume match with items.
            user: User profile.

        Returns:
            JSON-serializable resume dict with ALL user data.
        """
        import asyncio

        # Get included items for tracking which bullets are matched
        included_items = [item for item in match.items if item.included_in_resume]

        # Build sets of matched bullet IDs for highlighting
        matched_exp_bullet_ids = {
            item.experience_bullet_id
            for item in included_items
            if item.experience_bullet_id
        }
        matched_proj_bullet_ids = {
            item.project_bullet_id
            for item in included_items
            if item.project_bullet_id
        }

        # Execute all 4 queries in parallel using asyncio.gather()
        exp_query = db.execute(
            select(Experience)
            .options(selectinload(Experience.bullets))
            .where(
                Experience.user_id == user.id,
                Experience.deleted_at.is_(None),
            )
            .order_by(Experience.start_date.desc())
        )
        proj_query = db.execute(
            select(Project)
            .options(selectinload(Project.bullets), selectinload(Project.links))
            .where(
                Project.user_id == user.id,
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at.desc())
        )
        skill_query = db.execute(
            select(Skill)
            .where(
                Skill.user_id == user.id,
                Skill.deleted_at.is_(None),
            )
            .order_by(Skill.display_order)
        )
        pub_query = db.execute(
            select(Publication)
            .where(
                Publication.user_id == user.id,
                Publication.deleted_at.is_(None),
            )
            .order_by(Publication.display_order)
        )

        # Run all queries in parallel
        exp_result, proj_result, skill_result, pub_result = await asyncio.gather(
            exp_query, proj_query, skill_query, pub_query
        )

        all_experiences = exp_result.scalars().all()
        all_projects = proj_result.scalars().all()
        user_skills = [s.name for s in skill_result.scalars().all()]
        publications = pub_result.scalars().all()

        # Build experiences data with ALL bullets, marking matched ones
        experiences_data = []
        for exp in all_experiences:
            bullets_data = []
            for bullet in sorted(exp.bullets, key=lambda x: x.order_index):
                if bullet.deleted_at:
                    continue
                bullets_data.append({
                    "content": bullet.content,
                    "skills": bullet.skills,
                    "metrics": bullet.metrics,
                    "matched": bullet.id in matched_exp_bullet_ids,
                })

            experiences_data.append({
                "company": exp.company,
                "role": exp.role,
                "location": exp.location,
                "start_date": exp.start_date.isoformat() if exp.start_date else None,
                "end_date": exp.end_date.isoformat() if exp.end_date else None,
                "is_current": exp.is_current,
                "bullets": bullets_data,
            })

        # Build projects data with ALL bullets, marking matched ones
        projects_data = []
        for proj in all_projects:
            bullets_data = []
            for bullet in sorted(proj.bullets, key=lambda x: x.order_index):
                if bullet.deleted_at:
                    continue
                bullets_data.append({
                    "content": bullet.content,
                    "skills": bullet.skills,
                    "metrics": bullet.metrics,
                    "matched": bullet.id in matched_proj_bullet_ids,
                })

            projects_data.append({
                "name": proj.name,
                "description": proj.description,
                "technologies": proj.technologies,
                "start_date": proj.start_date.isoformat() if proj.start_date else None,
                "end_date": proj.end_date.isoformat() if proj.end_date else None,
                "bullets": bullets_data,
                "links": [
                    {"url": link.url, "type": link.link_type.value, "title": link.title}
                    for link in proj.links
                ],
            })

        # Build publications data
        publications_data = []
        for pub in publications:
            publications_data.append({
                "title": pub.title,
                "authors": pub.authors,
                "venue": pub.venue,
                "publication_date": pub.publication_date.isoformat() if pub.publication_date else None,
                "publication_type": pub.publication_type.value if pub.publication_type else None,
                "doi": pub.doi,
                "url": pub.url,
            })

        return {
            "profile": {
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "location": user.location,
                "linkedin_url": user.linkedin_url,
                "websites": user.websites,
                "summary": user.summary,
            },
            "target_job": {
                "company": match.job.company,
                "role": match.job.role,
                "location": match.job.location,
            },
            "match_score": {
                "overall": match.overall_match_score,
                "skill_coverage": match.skill_coverage,
                "experience_relevance": match.experience_relevance,
            },
            "experiences": experiences_data,
            "projects": projects_data,
            "skills": user_skills,
            "publications": publications_data,
        }

    async def generate_markdown(
        self,
        db: AsyncSession,
        match: ResumeMatch,
        user: User,
    ) -> str:
        """Generate resume as Markdown.

        Args:
            db: Database session.
            match: Resume match with items.
            user: User profile.

        Returns:
            Markdown-formatted resume string.
        """
        json_data = await self.generate_json(db, match, user)
        profile = json_data["profile"]

        lines = []

        # Header
        lines.append(f"# {profile['full_name'] or 'Resume'}")
        lines.append("")

        # Contact info
        contact_parts = []
        if profile.get("email"):
            contact_parts.append(profile["email"])
        if profile.get("phone"):
            contact_parts.append(profile["phone"])
        if profile.get("location"):
            contact_parts.append(profile["location"])
        if contact_parts:
            lines.append(" | ".join(contact_parts))
            lines.append("")

        # Links
        if profile.get("linkedin_url"):
            lines.append(f"[LinkedIn]({profile['linkedin_url']})")
        if profile.get("websites"):
            for website in profile["websites"]:
                lines.append(f"[Website]({website})")
        if profile.get("linkedin_url") or profile.get("websites"):
            lines.append("")

        # Summary
        if profile.get("summary"):
            lines.append("## Summary")
            lines.append("")
            lines.append(profile["summary"])
            lines.append("")

        # Experience
        if json_data["experiences"]:
            lines.append("## Experience")
            lines.append("")
            for exp in json_data["experiences"]:
                date_str = exp["start_date"] or ""
                if exp["is_current"]:
                    date_str += " - Present"
                elif exp["end_date"]:
                    date_str += f" - {exp['end_date']}"

                lines.append(f"### {exp['role']} at {exp['company']}")
                location_date = []
                if exp.get("location"):
                    location_date.append(exp["location"])
                if date_str:
                    location_date.append(date_str)
                if location_date:
                    lines.append(f"*{' | '.join(location_date)}*")
                lines.append("")

                for bullet in exp["bullets"]:
                    lines.append(f"- {bullet['content']}")
                lines.append("")

        # Projects
        if json_data["projects"]:
            lines.append("## Projects")
            lines.append("")
            for proj in json_data["projects"]:
                lines.append(f"### {proj['name']}")
                if proj.get("technologies"):
                    lines.append(f"*Technologies: {', '.join(proj['technologies'])}*")
                lines.append("")

                if proj.get("description"):
                    lines.append(proj["description"])
                    lines.append("")

                for bullet in proj["bullets"]:
                    lines.append(f"- {bullet['content']}")

                if proj.get("links"):
                    links_str = " | ".join(
                        f"[{link['type'].title()}]({link['url']})"
                        for link in proj["links"]
                    )
                    lines.append(f"\n{links_str}")
                lines.append("")

        # Skills
        if json_data["skills"]:
            lines.append("## Skills")
            lines.append("")
            lines.append(", ".join(json_data["skills"]))
            lines.append("")

        # Publications
        if json_data.get("publications"):
            lines.append("## Publications")
            lines.append("")
            for pub in json_data["publications"]:
                title = pub["title"]
                venue = pub.get("venue", "")
                date = pub.get("publication_date", "")
                pub_type = pub.get("publication_type", "")
                doi = pub.get("doi", "")
                url = pub.get("url", "")

                # Build publication entry
                entry = f"**{title}**"
                if venue:
                    entry += f" - {venue}"
                if date:
                    entry += f" ({date})"
                lines.append(f"- {entry}")

                # Add DOI or URL if available
                if doi:
                    lines.append(f"  DOI: {doi}")
                elif url:
                    lines.append(f"  [{url}]({url})")
            lines.append("")

        return "\n".join(lines)

    async def generate_google_doc(
        self,
        db: AsyncSession,
        match: ResumeMatch,
        user: User,
        credentials: dict[str, Any] | None = None,
    ) -> str | None:
        """Generate resume as ATS-friendly Google Doc.

        Args:
            db: Database session.
            match: Resume match with items.
            user: User profile.
            credentials: Google OAuth2 credentials with access_token.

        Returns:
            Google Doc URL or None if creation failed.
        """
        if not credentials or "access_token" not in credentials:
            logger.warning("Google Doc generation requires OAuth2 credentials")
            return None

        try:
            from src.integrations.google_docs import GoogleDocsService

            # Generate JSON data for structured formatting
            resume_data = await self.generate_json(db, match, user)

            # Create Google Doc with ATS-friendly formatting
            google_docs = GoogleDocsService(credentials=credentials)
            try:
                # Create title from user name and target role
                title = f"Resume - {user.full_name or 'Untitled'}"
                if match.job and match.job.role:
                    title += f" - {match.job.role}"
                if match.job and match.job.company:
                    title += f" at {match.job.company}"

                doc_url = await google_docs.create_ats_resume(
                    title=title,
                    resume_data=resume_data,
                )
                logger.info(f"Created ATS-friendly Google Doc: {doc_url}")
                return doc_url

            finally:
                await google_docs.close()

        except ValueError as e:
            logger.error(f"Google Doc creation failed: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error creating Google Doc: {e}")
            return None

    async def generate_optimized(
        self,
        db: AsyncSession,
        match: ResumeMatch,
        user: User,
        llm_client: Any,
        format: Literal["json", "markdown", "google_doc"] = "json",
        template: Literal["standard", "technical", "academic"] = "standard",
        max_experiences: int = 4,
        max_projects: int = 3,
        credentials: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate optimized resume using multi-agent system.

        This method uses three specialized agents:
        1. CollectionAgent - Gathers all user data
        2. MappingAgent - Scores and maps content to job requirements
        3. ResumeBuilderAgent - Creates ATS-friendly output

        Args:
            db: Database session.
            match: Resume match with job context.
            user: User profile.
            llm_client: LLM client for agents.
            format: Output format.
            template: ATS template type.
            max_experiences: Maximum experiences to include.
            max_projects: Maximum projects to include.
            credentials: Google OAuth2 credentials (for google_doc format).

        Returns:
            Dict with resume content and quality metrics.
        """
        from src.agents.resume_generation_supervisor import ResumeGenerationSupervisor
        from src.models.schemas.resume_generation import ResumeGenerationOptions

        logger.info(f"Starting multi-agent resume generation for user {user.id}")

        # Create supervisor and options
        supervisor = ResumeGenerationSupervisor(llm_client, db)
        options = ResumeGenerationOptions(
            format=format,
            max_experiences=max_experiences,
            max_projects=max_projects,
            template=template,
        )

        # Generate using multi-agent pipeline
        result = await supervisor.generate(user, match, options)

        # Build response
        response = {
            "json_data": result.json_data,
            "markdown": result.markdown,
            "ats_score": result.ats_score,
            "keyword_density": result.keyword_density,
            "optimization_notes": [
                {
                    "category": note.category,
                    "message": note.message,
                    "severity": note.severity,
                }
                for note in result.optimization_notes
            ],
            "stats": {
                "experiences_included": result.experiences_included,
                "projects_included": result.projects_included,
                "skills_included": result.skills_included,
                "publications_included": result.publications_included,
            },
        }

        # If Google Doc format, create the doc
        if format == "google_doc" and credentials:
            try:
                from src.integrations.google_docs import GoogleDocsService

                google_docs = GoogleDocsService(credentials=credentials)
                try:
                    title = f"Resume - {user.full_name or 'Untitled'}"
                    if match.job and match.job.role:
                        title += f" - {match.job.role}"

                    doc_url = await google_docs.create_ats_resume(
                        title=title,
                        resume_data=result.json_data,
                    )
                    response["google_doc_url"] = doc_url
                    logger.info(f"Created ATS-friendly Google Doc: {doc_url}")
                finally:
                    await google_docs.close()

            except Exception as e:
                logger.error(f"Google Doc creation failed: {e}")
                response["google_doc_error"] = str(e)

        return response


# Singleton instance
_resume_generator: ResumeGenerator | None = None


def get_resume_generator() -> ResumeGenerator:
    """Get or create the resume generator singleton."""
    global _resume_generator
    if _resume_generator is None:
        _resume_generator = ResumeGenerator()
    return _resume_generator
