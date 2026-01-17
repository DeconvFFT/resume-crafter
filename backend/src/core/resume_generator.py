"""Resume generation in multiple formats."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.database import (
    Experience,
    Project,
    ResumeMatch,
    ResumeMatchItem,
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
            JSON-serializable resume dict.
        """
        # Get included items with their bullets
        included_items = [item for item in match.items if item.included_in_resume]

        # Group by experience/project
        experience_bullets = {}
        project_bullets = {}

        for item in included_items:
            if item.experience_bullet:
                exp_id = item.experience_bullet.experience_id
                if exp_id not in experience_bullets:
                    experience_bullets[exp_id] = []
                experience_bullets[exp_id].append(item.experience_bullet)
            elif item.project_bullet:
                proj_id = item.project_bullet.project_id
                if proj_id not in project_bullets:
                    project_bullets[proj_id] = []
                project_bullets[proj_id].append(item.project_bullet)

        # Fetch full experience data
        experiences_data = []
        if experience_bullets:
            result = await db.execute(
                select(Experience)
                .where(Experience.id.in_(experience_bullets.keys()))
                .order_by(Experience.start_date.desc())
            )
            for exp in result.scalars():
                bullets = experience_bullets.get(exp.id, [])
                experiences_data.append({
                    "company": exp.company,
                    "role": exp.role,
                    "location": exp.location,
                    "start_date": exp.start_date.isoformat() if exp.start_date else None,
                    "end_date": exp.end_date.isoformat() if exp.end_date else None,
                    "is_current": exp.is_current,
                    "bullets": [
                        {
                            "content": b.content,
                            "skills": b.skills,
                            "metrics": b.metrics,
                        }
                        for b in sorted(bullets, key=lambda x: x.order_index)
                    ],
                })

        # Fetch full project data
        projects_data = []
        if project_bullets:
            result = await db.execute(
                select(Project)
                .options(selectinload(Project.links))
                .where(Project.id.in_(project_bullets.keys()))
                .order_by(Project.created_at.desc())
            )
            for proj in result.scalars():
                bullets = project_bullets.get(proj.id, [])
                projects_data.append({
                    "name": proj.name,
                    "description": proj.description,
                    "technologies": proj.technologies,
                    "start_date": proj.start_date.isoformat() if proj.start_date else None,
                    "end_date": proj.end_date.isoformat() if proj.end_date else None,
                    "bullets": [
                        {
                            "content": b.content,
                            "skills": b.skills,
                            "metrics": b.metrics,
                        }
                        for b in sorted(bullets, key=lambda x: x.order_index)
                    ],
                    "links": [
                        {"url": link.url, "type": link.link_type.value, "title": link.title}
                        for link in proj.links
                    ],
                })

        # Collect all skills
        all_skills = set()
        for item in included_items:
            if item.experience_bullet and item.experience_bullet.skills:
                all_skills.update(item.experience_bullet.skills)
            if item.project_bullet and item.project_bullet.skills:
                all_skills.update(item.project_bullet.skills)

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
            "skills": sorted(all_skills),
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

        return "\n".join(lines)

    async def generate_google_doc(
        self,
        db: AsyncSession,
        match: ResumeMatch,
        user: User,
        credentials: dict[str, Any] | None = None,
    ) -> str | None:
        """Generate resume as Google Doc.

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

            # Generate markdown content first
            markdown_content = await self.generate_markdown(db, match, user)

            # Create Google Doc
            google_docs = GoogleDocsService(credentials=credentials)
            try:
                # Create title from user name and target role
                title = f"Resume - {user.full_name or 'Untitled'}"
                if match.job and match.job.role:
                    title += f" - {match.job.role}"
                if match.job and match.job.company:
                    title += f" at {match.job.company}"

                doc_url = await google_docs.create_document(
                    title=title,
                    content=markdown_content,
                )
                logger.info(f"Created Google Doc: {doc_url}")
                return doc_url

            finally:
                await google_docs.close()

        except ValueError as e:
            logger.error(f"Google Doc creation failed: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error creating Google Doc: {e}")
            return None


# Singleton instance
_resume_generator: ResumeGenerator | None = None


def get_resume_generator() -> ResumeGenerator:
    """Get or create the resume generator singleton."""
    global _resume_generator
    if _resume_generator is None:
        _resume_generator = ResumeGenerator()
    return _resume_generator
