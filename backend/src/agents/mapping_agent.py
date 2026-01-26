"""Mapping Agent for scoring and mapping user content to job requirements.

This agent analyzes user experiences, projects, and skills against
job requirements to determine relevance and identify gaps.
"""

import logging
from typing import Any
from uuid import UUID

from src.models.schemas.resume_generation import (
    BulletData,
    CollectedResumeData,
    ExperienceData,
    JobRequirementData,
    MappedResumeData,
    ProjectData,
    ScoredBullet,
    ScoredExperience,
    ScoredProject,
    ScoredSkill,
    SkillData,
)

logger = logging.getLogger(__name__)


class MappingAgent:
    """Agent that maps and scores user content against job requirements.

    This agent:
    1. Scores each bullet point's relevance to job requirements
    2. Identifies which requirements each bullet addresses
    3. Matches user skills to required skills
    4. Calculates overall fit score
    5. Identifies skill gaps

    Uses LLM for intelligent relevance scoring.
    """

    def __init__(self, llm_client: Any):
        """Initialize the mapping agent.

        Args:
            llm_client: LLM client for scoring operations.
        """
        self._llm = llm_client

    async def run(
        self,
        collected: CollectedResumeData,
    ) -> MappedResumeData:
        """Map and score collected data against job requirements.

        Args:
            collected: Collected resume data from CollectionAgent.

        Returns:
            MappedResumeData with scored content and analysis.
        """
        logger.info("MappingAgent: Scoring content against job requirements")

        # Score experiences
        scored_experiences = await self._score_experiences(
            collected.experiences,
            collected.requirements,
        )

        # Score projects
        scored_projects = await self._score_projects(
            collected.projects,
            collected.requirements,
        )

        # Match skills
        scored_skills, skill_gaps = self._match_skills(
            collected.skills,
            collected.requirements,
        )

        # Calculate requirement coverage
        requirement_coverage = self._calculate_coverage(
            scored_experiences,
            scored_projects,
            collected.requirements,
        )

        # Calculate overall fit score
        overall_fit = self._calculate_fit_score(
            scored_experiences,
            scored_projects,
            scored_skills,
            collected.requirements,
        )

        logger.info(
            f"MappingAgent: Overall fit score: {overall_fit:.2f}, "
            f"Skill gaps: {len(skill_gaps)}"
        )

        return MappedResumeData(
            profile=collected.profile,
            experiences=scored_experiences,
            projects=scored_projects,
            skills=scored_skills,
            publications=collected.publications,
            job_id=collected.job_id,
            job_company=collected.job_company,
            job_role=collected.job_role,
            requirement_coverage=requirement_coverage,
            skill_gaps=skill_gaps,
            overall_fit_score=overall_fit,
        )

    async def _score_experiences(
        self,
        experiences: list[ExperienceData],
        requirements: list[JobRequirementData],
    ) -> list[ScoredExperience]:
        """Score experience bullets against requirements."""
        scored_experiences = []

        for exp in experiences:
            scored_bullets = await self._score_bullets(
                exp.bullets,
                requirements,
                context=f"{exp.role} at {exp.company}",
            )

            # Calculate overall experience score (average of bullet scores)
            if scored_bullets:
                overall_score = sum(b.relevance_score for b in scored_bullets) / len(
                    scored_bullets
                )
            else:
                overall_score = 0.0

            scored_experiences.append(
                ScoredExperience(
                    experience=exp,
                    bullets=scored_bullets,
                    overall_score=overall_score,
                )
            )

        # Sort by overall score descending
        scored_experiences.sort(key=lambda x: x.overall_score, reverse=True)
        return scored_experiences

    async def _score_projects(
        self,
        projects: list[ProjectData],
        requirements: list[JobRequirementData],
    ) -> list[ScoredProject]:
        """Score project bullets against requirements."""
        scored_projects = []

        for proj in projects:
            scored_bullets = await self._score_bullets(
                proj.bullets,
                requirements,
                context=f"Project: {proj.name}",
            )

            if scored_bullets:
                overall_score = sum(b.relevance_score for b in scored_bullets) / len(
                    scored_bullets
                )
            else:
                # Also consider project description and technologies
                overall_score = self._score_project_metadata(proj, requirements)

            scored_projects.append(
                ScoredProject(
                    project=proj,
                    bullets=scored_bullets,
                    overall_score=overall_score,
                )
            )

        scored_projects.sort(key=lambda x: x.overall_score, reverse=True)
        return scored_projects

    async def _score_bullets(
        self,
        bullets: list[BulletData],
        requirements: list[JobRequirementData],
        context: str,
    ) -> list[ScoredBullet]:
        """Score individual bullets against requirements using LLM."""
        if not bullets or not requirements:
            return []

        scored_bullets = []

        # Build requirements context for LLM
        req_texts = [
            f"- [{req.requirement_type}] {req.content}"
            for req in requirements
        ]
        requirements_context = "\n".join(req_texts)

        for bullet in bullets:
            try:
                # Use LLM to score bullet relevance
                score, matched_reqs, explanation = await self._llm_score_bullet(
                    bullet.content,
                    requirements_context,
                    requirements,
                    context,
                )

                scored_bullets.append(
                    ScoredBullet(
                        bullet=bullet,
                        relevance_score=score,
                        matched_requirements=matched_reqs,
                        explanation=explanation,
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to score bullet: {e}")
                # Fallback to keyword matching
                score = self._keyword_score(bullet, requirements)
                scored_bullets.append(
                    ScoredBullet(
                        bullet=bullet,
                        relevance_score=score,
                        matched_requirements=[],
                        explanation="Scored by keyword matching (LLM unavailable)",
                    )
                )

        # Sort by relevance score
        scored_bullets.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_bullets

    async def _llm_score_bullet(
        self,
        bullet_content: str,
        requirements_context: str,
        requirements: list[JobRequirementData],
        context: str,
    ) -> tuple[float, list[UUID], str]:
        """Use LLM to score a bullet's relevance to requirements."""
        prompt = f"""Score the relevance of this resume bullet point to the job requirements.

Context: {context}

Bullet Point:
{bullet_content}

Job Requirements:
{requirements_context}

Analyze how well this bullet demonstrates skills, experience, or qualifications matching the requirements.

Return a JSON object with:
- score: float from 0.0 (irrelevant) to 1.0 (highly relevant)
- matched_indices: list of 0-based indices of requirements this bullet addresses
- explanation: brief explanation of the score

Consider:
- Direct skill or experience match
- Transferable skills
- Quantified achievements
- Scope and impact similarity
"""
        try:
            response = await self._llm.generate(prompt)

            # Parse response - expecting JSON
            import json
            import re

            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                score = float(result.get("score", 0.5))
                matched_indices = result.get("matched_indices", [])
                explanation = result.get("explanation", "")

                # Convert indices to requirement UUIDs
                matched_req_ids = [
                    requirements[i].id
                    for i in matched_indices
                    if 0 <= i < len(requirements)
                ]

                return min(max(score, 0.0), 1.0), matched_req_ids, explanation

        except Exception as e:
            logger.debug(f"LLM scoring failed: {e}")

        # Fallback
        return 0.5, [], "Default score"

    def _keyword_score(
        self,
        bullet: BulletData,
        requirements: list[JobRequirementData],
    ) -> float:
        """Simple keyword-based scoring fallback."""
        bullet_lower = bullet.content.lower()
        bullet_skills = set(s.lower() for s in bullet.skills)

        total_score = 0.0
        for req in requirements:
            # Check if requirement keywords appear in bullet
            keywords = [k.lower() for k in req.keywords]
            matches = sum(1 for k in keywords if k in bullet_lower or k in bullet_skills)
            if keywords:
                total_score += (matches / len(keywords)) * (req.importance_score / 5)

        if requirements:
            return min(total_score / len(requirements), 1.0)
        return 0.0

    def _score_project_metadata(
        self,
        project: ProjectData,
        requirements: list[JobRequirementData],
    ) -> float:
        """Score project based on technologies and description."""
        score = 0.0
        tech_lower = set(t.lower() for t in project.technologies)

        for req in requirements:
            keywords = [k.lower() for k in req.keywords]
            tech_matches = sum(1 for k in keywords if k in tech_lower)
            if keywords:
                score += (tech_matches / len(keywords)) * (req.importance_score / 5)

        if requirements:
            return min(score / len(requirements), 1.0)
        return 0.0

    def _match_skills(
        self,
        skills: list[SkillData],
        requirements: list[JobRequirementData],
    ) -> tuple[list[ScoredSkill], list[str]]:
        """Match user skills to required skills and identify gaps."""
        scored_skills = []
        skill_names_lower = {s.name.lower(): s for s in skills}

        # Extract required skills from requirements
        required_skills = set()
        for req in requirements:
            if req.requirement_type == "skill":
                required_skills.update(k.lower() for k in req.keywords)
            else:
                required_skills.update(k.lower() for k in req.keywords)

        # Match skills
        matched_required = set()
        for skill in skills:
            skill_lower = skill.name.lower()
            is_required = skill_lower in required_skills

            # Find which requirements this skill matches
            matched_req_ids = []
            for req in requirements:
                if any(skill_lower in k.lower() or k.lower() in skill_lower
                       for k in req.keywords):
                    matched_req_ids.append(req.id)
                    matched_required.add(skill_lower)

            scored_skills.append(
                ScoredSkill(
                    skill=skill,
                    is_required=is_required or bool(matched_req_ids),
                    matched_requirement_ids=matched_req_ids,
                )
            )

        # Identify gaps (required skills user lacks)
        skill_gaps = [
            skill for skill in required_skills
            if skill not in matched_required and skill not in skill_names_lower
        ]

        # Sort: required skills first
        scored_skills.sort(key=lambda x: (not x.is_required, x.skill.name))
        return scored_skills, skill_gaps

    def _calculate_coverage(
        self,
        experiences: list[ScoredExperience],
        projects: list[ScoredProject],
        requirements: list[JobRequirementData],
    ) -> dict[str, list[str]]:
        """Calculate which bullets cover each requirement."""
        coverage: dict[str, list[str]] = {}

        for req in requirements:
            covered_by = []

            # Check experience bullets
            for exp in experiences:
                for bullet in exp.bullets:
                    if req.id in bullet.matched_requirements:
                        covered_by.append(bullet.bullet.content)

            # Check project bullets
            for proj in projects:
                for bullet in proj.bullets:
                    if req.id in bullet.matched_requirements:
                        covered_by.append(bullet.bullet.content)

            coverage[str(req.id)] = covered_by

        return coverage

    def _calculate_fit_score(
        self,
        experiences: list[ScoredExperience],
        projects: list[ScoredProject],
        skills: list[ScoredSkill],
        requirements: list[JobRequirementData],
    ) -> float:
        """Calculate overall fit score."""
        if not requirements:
            return 0.0

        # Experience relevance (weighted by importance)
        exp_scores = []
        for exp in experiences:
            for bullet in exp.bullets:
                if bullet.relevance_score > 0.3:
                    exp_scores.append(bullet.relevance_score)

        exp_avg = sum(exp_scores) / len(exp_scores) if exp_scores else 0.0

        # Project relevance
        proj_scores = []
        for proj in projects:
            for bullet in proj.bullets:
                if bullet.relevance_score > 0.3:
                    proj_scores.append(bullet.relevance_score)

        proj_avg = sum(proj_scores) / len(proj_scores) if proj_scores else 0.0

        # Skill coverage
        required_skills = [s for s in skills if s.is_required]
        skill_coverage = len(required_skills) / len(requirements) if requirements else 0.0

        # Combine (weighted average)
        # Experience: 50%, Projects: 30%, Skills: 20%
        overall = (exp_avg * 0.5) + (proj_avg * 0.3) + (skill_coverage * 0.2)

        return min(max(overall, 0.0), 1.0)
