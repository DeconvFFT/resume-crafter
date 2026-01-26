"""Resume Builder Agent for creating ATS-friendly resumes.

This agent applies ATS template knowledge to create optimized resumes
from mapped and scored user content.
"""

import logging
from datetime import datetime
from typing import Any

from src.models.schemas.resume_generation import (
    ATS_TEMPLATES,
    GeneratedResumeResult,
    MappedResumeData,
    OptimizationNote,
    ResumeGenerationOptions,
    ScoredExperience,
    ScoredProject,
)

logger = logging.getLogger(__name__)


class ResumeBuilderAgent:
    """Agent that builds ATS-friendly resumes from mapped data.

    This agent:
    1. Selects top content based on relevance scores
    2. Applies ATS template rules
    3. Generates resume in multiple formats
    4. Calculates ATS compatibility score
    5. Provides optimization suggestions

    Embeds ATS best practices and template knowledge.
    """

    def __init__(self, llm_client: Any | None = None):
        """Initialize the resume builder agent.

        Args:
            llm_client: Optional LLM client for advanced optimization.
        """
        self._llm = llm_client

    async def run(
        self,
        mapped: MappedResumeData,
        options: ResumeGenerationOptions,
    ) -> GeneratedResumeResult:
        """Build ATS-friendly resume from mapped data.

        Args:
            mapped: Mapped and scored resume data.
            options: Generation configuration options.

        Returns:
            GeneratedResumeResult with resume content and quality metrics.
        """
        logger.info(f"ResumeBuilderAgent: Building {options.template} resume")

        template = ATS_TEMPLATES.get(options.template, ATS_TEMPLATES["standard"])

        # Select top content
        selected_experiences = self._select_experiences(
            mapped.experiences,
            options.max_experiences,
            options.max_bullets_per_experience,
            options.relevance_threshold,
        )

        selected_projects = self._select_projects(
            mapped.projects,
            options.max_projects,
            options.max_bullets_per_project,
            options.relevance_threshold,
        )

        selected_skills = self._select_skills(
            mapped.skills,
            options.include_all_skills,
        )

        selected_publications = (
            mapped.publications if options.include_publications else []
        )

        # Build JSON structure
        json_data = self._build_json(
            profile=mapped.profile,
            experiences=selected_experiences,
            projects=selected_projects,
            skills=selected_skills,
            publications=selected_publications,
            job_company=mapped.job_company,
            job_role=mapped.job_role,
            template=template,
        )

        # Build markdown
        markdown = self._build_markdown(json_data, template)

        # Calculate ATS score
        ats_score = self._calculate_ats_score(json_data, template)

        # Generate optimization notes
        optimization_notes = self._generate_optimization_notes(
            json_data,
            mapped,
            template,
        )

        logger.info(
            f"ResumeBuilderAgent: Generated resume with ATS score {ats_score:.0f}"
        )

        return GeneratedResumeResult(
            json_data=json_data,
            markdown=markdown,
            ats_score=ats_score,
            keyword_density=self._calculate_keyword_density(
                markdown, mapped.requirement_coverage
            ),
            optimization_notes=optimization_notes,
            experiences_included=len(selected_experiences),
            projects_included=len(selected_projects),
            skills_included=len(selected_skills),
            publications_included=len(selected_publications),
        )

    def _select_experiences(
        self,
        experiences: list[ScoredExperience],
        max_count: int,
        max_bullets: int,
        threshold: float,
    ) -> list[dict]:
        """Select top experiences and bullets."""
        selected = []

        for exp in experiences[:max_count]:
            # Select top bullets above threshold
            top_bullets = [
                {
                    "content": b.bullet.content,
                    "skills": b.bullet.skills,
                    "metrics": b.bullet.metrics,
                    "relevance_score": b.relevance_score,
                }
                for b in exp.bullets
                if b.relevance_score >= threshold
            ][:max_bullets]

            # If no bullets above threshold, take top ones anyway
            if not top_bullets and exp.bullets:
                top_bullets = [
                    {
                        "content": b.bullet.content,
                        "skills": b.bullet.skills,
                        "metrics": b.bullet.metrics,
                        "relevance_score": b.relevance_score,
                    }
                    for b in exp.bullets[:max_bullets]
                ]

            selected.append({
                "company": exp.experience.company,
                "role": exp.experience.role,
                "location": exp.experience.location,
                "start_date": exp.experience.start_date,
                "end_date": exp.experience.end_date,
                "is_current": exp.experience.is_current,
                "bullets": top_bullets,
                "overall_score": exp.overall_score,
            })

        return selected

    def _select_projects(
        self,
        projects: list[ScoredProject],
        max_count: int,
        max_bullets: int,
        threshold: float,
    ) -> list[dict]:
        """Select top projects and bullets."""
        selected = []

        for proj in projects[:max_count]:
            top_bullets = [
                {
                    "content": b.bullet.content,
                    "skills": b.bullet.skills,
                    "metrics": b.bullet.metrics,
                    "relevance_score": b.relevance_score,
                }
                for b in proj.bullets
                if b.relevance_score >= threshold
            ][:max_bullets]

            if not top_bullets and proj.bullets:
                top_bullets = [
                    {
                        "content": b.bullet.content,
                        "skills": b.bullet.skills,
                        "metrics": b.bullet.metrics,
                        "relevance_score": b.relevance_score,
                    }
                    for b in proj.bullets[:max_bullets]
                ]

            selected.append({
                "name": proj.project.name,
                "description": proj.project.description,
                "technologies": proj.project.technologies,
                "start_date": proj.project.start_date,
                "end_date": proj.project.end_date,
                "bullets": top_bullets,
                "links": proj.project.links,
                "overall_score": proj.overall_score,
            })

        return selected

    def _select_skills(
        self,
        skills: list,
        include_all: bool,
    ) -> list[dict]:
        """Select skills for resume."""
        if include_all:
            return [
                {
                    "name": s.skill.name,
                    "category": s.skill.category,
                    "is_required": s.is_required,
                }
                for s in skills
            ]
        else:
            # Only include required/matched skills
            return [
                {
                    "name": s.skill.name,
                    "category": s.skill.category,
                    "is_required": s.is_required,
                }
                for s in skills
                if s.is_required
            ]

    def _build_json(
        self,
        profile: dict,
        experiences: list[dict],
        projects: list[dict],
        skills: list[dict],
        publications: list,
        job_company: str | None,
        job_role: str | None,
        template: dict,
    ) -> dict:
        """Build JSON resume structure."""
        # Group skills by category
        skills_by_category: dict[str, list[str]] = {}
        for skill in skills:
            category = skill.get("category") or "Other"
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill["name"])

        # Build publications data
        publications_data = []
        for pub in publications:
            publications_data.append({
                "title": pub.title,
                "authors": pub.authors,
                "venue": pub.venue,
                "publication_date": pub.publication_date,
                "publication_type": pub.publication_type,
                "doi": pub.doi,
                "url": pub.url,
            })

        return {
            "profile": profile,
            "target_job": {
                "company": job_company,
                "role": job_role,
            },
            "experiences": experiences,
            "projects": projects,
            "skills": [s["name"] for s in skills],  # Flat list for compatibility
            "skills_by_category": skills_by_category,
            "publications": publications_data,
            "template": template,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _build_markdown(self, json_data: dict, template: dict) -> str:
        """Build ATS-friendly markdown resume."""
        lines = []
        profile = json_data["profile"]

        # Header - Name (Large)
        name = profile.get("full_name") or "Resume"
        lines.append(f"# {name}")
        lines.append("")

        # Contact Info (Single line)
        contact_parts = []
        if profile.get("email"):
            contact_parts.append(profile["email"])
        if profile.get("phone"):
            contact_parts.append(profile["phone"])
        if profile.get("location"):
            contact_parts.append(profile["location"])
        if profile.get("linkedin_url"):
            contact_parts.append(profile["linkedin_url"])

        if contact_parts:
            lines.append(" | ".join(contact_parts))
            lines.append("")

        # Summary
        if profile.get("summary"):
            lines.append("## SUMMARY")
            lines.append("")
            lines.append(profile["summary"])
            lines.append("")

        # Experience
        if json_data.get("experiences"):
            lines.append("## EXPERIENCE")
            lines.append("")

            for exp in json_data["experiences"]:
                # Role at Company
                lines.append(f"### {exp['role']} at {exp['company']}")

                # Location | Dates
                meta_parts = []
                if exp.get("location"):
                    meta_parts.append(exp["location"])
                date_str = self._format_date_range(
                    exp.get("start_date"),
                    exp.get("end_date"),
                    exp.get("is_current", False),
                )
                if date_str:
                    meta_parts.append(date_str)
                if meta_parts:
                    lines.append(f"*{' | '.join(meta_parts)}*")
                lines.append("")

                # Bullets
                for bullet in exp.get("bullets", []):
                    content = bullet.get("content", "")
                    lines.append(f"- {content}")
                lines.append("")

        # Projects
        if json_data.get("projects"):
            lines.append("## PROJECTS")
            lines.append("")

            for proj in json_data["projects"]:
                lines.append(f"### {proj['name']}")

                if proj.get("technologies"):
                    lines.append(f"*Technologies: {', '.join(proj['technologies'])}*")
                lines.append("")

                if proj.get("description"):
                    lines.append(proj["description"])
                    lines.append("")

                for bullet in proj.get("bullets", []):
                    content = bullet.get("content", "")
                    lines.append(f"- {content}")

                if proj.get("links"):
                    links_str = " | ".join(
                        link.get("url", "") for link in proj["links"] if link.get("url")
                    )
                    if links_str:
                        lines.append(f"\nLinks: {links_str}")
                lines.append("")

        # Skills
        if json_data.get("skills"):
            lines.append("## SKILLS")
            lines.append("")

            # Use categorized skills if available
            if json_data.get("skills_by_category"):
                for category, skill_list in json_data["skills_by_category"].items():
                    lines.append(f"**{category}:** {', '.join(skill_list)}")
            else:
                lines.append(", ".join(json_data["skills"]))
            lines.append("")

        # Publications
        if json_data.get("publications"):
            lines.append("## PUBLICATIONS")
            lines.append("")

            for pub in json_data["publications"]:
                title = pub.get("title", "Untitled")
                lines.append(f"**{title}**")

                meta_parts = []
                if pub.get("authors"):
                    authors = pub["authors"]
                    if isinstance(authors, list):
                        authors = ", ".join(authors)
                    meta_parts.append(authors)
                if pub.get("venue"):
                    meta_parts.append(pub["venue"])
                if pub.get("publication_date"):
                    meta_parts.append(pub["publication_date"])

                if meta_parts:
                    lines.append(f"*{' | '.join(meta_parts)}*")

                if pub.get("doi"):
                    lines.append(f"DOI: {pub['doi']}")
                elif pub.get("url"):
                    lines.append(f"[Link]({pub['url']})")
                lines.append("")

        return "\n".join(lines)

    def _format_date_range(
        self,
        start_date: str | None,
        end_date: str | None,
        is_current: bool,
    ) -> str:
        """Format date range for display."""
        if not start_date:
            return ""

        try:
            start = datetime.fromisoformat(start_date)
            start_str = start.strftime("%b %Y")
        except (ValueError, TypeError):
            start_str = start_date[:7] if start_date and len(start_date) >= 7 else start_date or ""

        if is_current:
            return f"{start_str} - Present"
        elif end_date:
            try:
                end = datetime.fromisoformat(end_date)
                end_str = end.strftime("%b %Y")
            except (ValueError, TypeError):
                end_str = end_date[:7] if end_date and len(end_date) >= 7 else end_date
            return f"{start_str} - {end_str}"
        else:
            return start_str

    def _calculate_ats_score(self, json_data: dict, template: dict) -> float:
        """Calculate ATS compatibility score (0-100)."""
        score = 100.0
        rules = template.get("rules", [])

        # Check contact info
        profile = json_data.get("profile", {})
        if not profile.get("email"):
            score -= 15
        if not profile.get("phone"):
            score -= 5

        # Check experiences have bullets
        for exp in json_data.get("experiences", []):
            if not exp.get("bullets"):
                score -= 5

        # Check for action verbs in bullets
        action_verbs = {
            "developed", "implemented", "designed", "managed", "led", "created",
            "built", "launched", "improved", "increased", "decreased", "achieved",
            "delivered", "optimized", "automated", "integrated", "analyzed",
            "collaborated", "coordinated", "established", "executed", "generated",
        }

        bullet_count = 0
        action_verb_count = 0
        for exp in json_data.get("experiences", []):
            for bullet in exp.get("bullets", []):
                bullet_count += 1
                content = bullet.get("content", "").lower()
                first_word = content.split()[0] if content.split() else ""
                if first_word in action_verbs:
                    action_verb_count += 1

        if bullet_count > 0:
            action_ratio = action_verb_count / bullet_count
            if action_ratio < 0.5:
                score -= (0.5 - action_ratio) * 20

        # Check for metrics in bullets
        metrics_count = 0
        for exp in json_data.get("experiences", []):
            for bullet in exp.get("bullets", []):
                content = bullet.get("content", "")
                if any(c.isdigit() for c in content) or "%" in content:
                    metrics_count += 1

        if bullet_count > 0:
            metrics_ratio = metrics_count / bullet_count
            if metrics_ratio < 0.3:
                score -= (0.3 - metrics_ratio) * 15

        # Check skills section
        if not json_data.get("skills"):
            score -= 10

        return max(score, 0.0)

    def _calculate_keyword_density(
        self,
        markdown: str,
        coverage: dict[str, list],
    ) -> float:
        """Calculate percentage of job keywords present in resume."""
        if not coverage:
            return 0.0

        covered_reqs = sum(1 for bullets in coverage.values() if bullets)
        total_reqs = len(coverage)

        return (covered_reqs / total_reqs * 100) if total_reqs else 0.0

    def _generate_optimization_notes(
        self,
        json_data: dict,
        mapped: MappedResumeData,
        template: dict,
    ) -> list[OptimizationNote]:
        """Generate suggestions for improving the resume."""
        notes = []

        # Check for skill gaps
        if mapped.skill_gaps:
            notes.append(
                OptimizationNote(
                    category="content",
                    message=f"Consider addressing these required skills: {', '.join(mapped.skill_gaps[:5])}",
                    severity="suggestion",
                )
            )

        # Check fit score
        if mapped.overall_fit_score < 0.5:
            notes.append(
                OptimizationNote(
                    category="content",
                    message="Your resume has low relevance to this job. Consider tailoring your bullets more specifically.",
                    severity="warning",
                )
            )

        # Check experience count
        if len(json_data.get("experiences", [])) < 2:
            notes.append(
                OptimizationNote(
                    category="content",
                    message="Consider adding more work experience if available.",
                    severity="info",
                )
            )

        # Check for metrics
        has_metrics = False
        for exp in json_data.get("experiences", []):
            for bullet in exp.get("bullets", []):
                content = bullet.get("content", "")
                if any(c.isdigit() for c in content):
                    has_metrics = True
                    break

        if not has_metrics:
            notes.append(
                OptimizationNote(
                    category="content",
                    message="Add quantifiable metrics to your bullet points (e.g., 'increased sales by 25%').",
                    severity="suggestion",
                )
            )

        # Check summary
        if not json_data.get("profile", {}).get("summary"):
            notes.append(
                OptimizationNote(
                    category="structure",
                    message="Consider adding a professional summary tailored to this role.",
                    severity="suggestion",
                )
            )

        return notes
