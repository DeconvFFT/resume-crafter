"""Job Qualification Agent for scoring jobs against user profile.

This agent:
1. Analyzes job requirements vs user skills/experience
2. Calculates match score (0-100)
3. Provides detailed match reasoning
4. Filters out unsuitable jobs
"""

import logging
import re
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SkillMatch(BaseModel):
    """Match analysis for a single skill."""
    skill: str
    required: bool = False
    user_has: bool = False
    proficiency_match: float = 0.0  # 0-1


class ExperienceMatch(BaseModel):
    """Match analysis for experience requirements."""
    years_required: int | None = None
    years_user_has: int = 0
    is_sufficient: bool = False
    relevant_roles: list[str] = Field(default_factory=list)


class QualificationResult(BaseModel):
    """Result of job qualification analysis."""
    job_id: str
    match_score: float = Field(ge=0, le=100)
    is_qualified: bool
    match_reasoning: str
    skill_matches: list[SkillMatch] = Field(default_factory=list)
    experience_match: ExperienceMatch | None = None
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    """Simplified user profile for matching."""
    skills: list[str] = Field(default_factory=list)
    skill_proficiencies: dict[str, str] = Field(default_factory=dict)  # skill -> level
    years_of_experience: int = 0
    job_titles: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)


class JobRequirements(BaseModel):
    """Extracted job requirements for matching."""
    job_id: str
    title: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    min_years_experience: int | None = None
    education_required: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None


class JobQualificationAgent:
    """Agent that scores and qualifies jobs against user profile.

    Scoring breakdown:
    - Skills match: 40 points
    - Experience match: 30 points
    - Role relevance: 20 points
    - Other factors: 10 points

    Qualification threshold: 60 points
    """

    SKILL_WEIGHT = 40
    EXPERIENCE_WEIGHT = 30
    ROLE_WEIGHT = 20
    OTHER_WEIGHT = 10
    QUALIFICATION_THRESHOLD = 60

    def __init__(self, llm_client: Any | None = None):
        """Initialize the qualification agent.

        Args:
            llm_client: LLM client for advanced requirement extraction.
        """
        self._llm = llm_client

    async def run(
        self,
        job_requirements: JobRequirements,
        user_profile: UserProfile,
    ) -> QualificationResult:
        """Score and qualify a job against user profile.

        Args:
            job_requirements: Extracted job requirements.
            user_profile: User's skills and experience.

        Returns:
            QualificationResult with score and reasoning.
        """
        logger.info(f"JobQualificationAgent: Analyzing job {job_requirements.job_id}")

        # Analyze skills match
        skill_score, skill_matches = self._analyze_skills(
            job_requirements.required_skills + job_requirements.preferred_skills,
            user_profile.skills,
            user_profile.skill_proficiencies,
        )

        # Analyze experience match
        exp_score, exp_match = self._analyze_experience(
            job_requirements.min_years_experience,
            user_profile.years_of_experience,
            user_profile.job_titles,
            job_requirements.title,
        )

        # Analyze role relevance
        role_score = self._analyze_role_relevance(
            job_requirements.title,
            user_profile.job_titles,
        )

        # Calculate total score
        total_score = (
            skill_score * (self.SKILL_WEIGHT / 100) +
            exp_score * (self.EXPERIENCE_WEIGHT / 100) +
            role_score * (self.ROLE_WEIGHT / 100) +
            self.OTHER_WEIGHT  # Base points
        )

        # Determine qualification
        is_qualified = total_score >= self.QUALIFICATION_THRESHOLD

        # Generate strengths and gaps
        strengths, gaps = self._identify_strengths_gaps(skill_matches, exp_match)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            total_score, skill_score, exp_score, role_score, strengths, gaps
        )

        return QualificationResult(
            job_id=job_requirements.job_id,
            match_score=round(total_score, 1),
            is_qualified=is_qualified,
            match_reasoning=reasoning,
            skill_matches=skill_matches,
            experience_match=exp_match,
            strengths=strengths,
            gaps=gaps,
        )

    async def batch_qualify(
        self,
        jobs: list[JobRequirements],
        user_profile: UserProfile,
        filter_unqualified: bool = True,
    ) -> list[QualificationResult]:
        """Qualify multiple jobs in batch.

        Args:
            jobs: List of job requirements.
            user_profile: User's profile.
            filter_unqualified: If True, only return qualified jobs.

        Returns:
            List of qualification results (optionally filtered).
        """
        results = []
        for job in jobs:
            result = await self.run(job, user_profile)
            if not filter_unqualified or result.is_qualified:
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.match_score, reverse=True)
        return results

    def extract_requirements(
        self,
        job_id: str,
        title: str,
        description: str,
        requirements_text: str | None = None,
    ) -> JobRequirements:
        """Extract structured requirements from job description.

        Uses regex patterns for now; LLM extraction in future.
        """
        text = f"{description or ''} {requirements_text or ''}".lower()

        # Extract skills (common tech skills)
        skill_patterns = [
            r'\b(python|java|javascript|typescript|go|rust|c\+\+|c#|ruby|php|swift|kotlin)\b',
            r'\b(react|angular|vue|node\.?js|django|flask|fastapi|spring|rails)\b',
            r'\b(aws|azure|gcp|kubernetes|docker|terraform|jenkins|ci/cd)\b',
            r'\b(sql|postgresql|mysql|mongodb|redis|elasticsearch)\b',
            r'\b(machine learning|ml|ai|deep learning|nlp|computer vision)\b',
        ]

        skills = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, text)
            skills.update(m.lower() for m in matches)

        # Extract years of experience
        years_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience', text)
        min_years = int(years_match.group(1)) if years_match else None

        return JobRequirements(
            job_id=job_id,
            title=title,
            required_skills=list(skills),
            min_years_experience=min_years,
        )

    def _analyze_skills(
        self,
        required_skills: list[str],
        user_skills: list[str],
        proficiencies: dict[str, str],
    ) -> tuple[float, list[SkillMatch]]:
        """Analyze skill match between job and user."""
        if not required_skills:
            return 100.0, []

        user_skills_lower = {s.lower() for s in user_skills}
        matches = []
        matched_count = 0

        for skill in required_skills:
            skill_lower = skill.lower()
            has_skill = skill_lower in user_skills_lower

            # Check proficiency
            prof_score = 0.0
            if has_skill:
                matched_count += 1
                prof = proficiencies.get(skill, "intermediate")
                prof_scores = {"beginner": 0.5, "intermediate": 0.75, "advanced": 0.9, "expert": 1.0}
                prof_score = prof_scores.get(prof, 0.75)

            matches.append(SkillMatch(
                skill=skill,
                required=True,
                user_has=has_skill,
                proficiency_match=prof_score,
            ))

        score = (matched_count / len(required_skills)) * 100
        return score, matches

    def _analyze_experience(
        self,
        required_years: int | None,
        user_years: int,
        user_titles: list[str],
        job_title: str,
    ) -> tuple[float, ExperienceMatch]:
        """Analyze experience match."""
        # Find relevant roles
        job_title_lower = job_title.lower()
        relevant = [t for t in user_titles if any(w in t.lower() for w in job_title_lower.split())]

        # Calculate score
        if required_years is None:
            score = 100.0
            is_sufficient = True
        elif user_years >= required_years:
            score = 100.0
            is_sufficient = True
        else:
            score = (user_years / required_years) * 100
            is_sufficient = False

        return score, ExperienceMatch(
            years_required=required_years,
            years_user_has=user_years,
            is_sufficient=is_sufficient,
            relevant_roles=relevant,
        )

    def _analyze_role_relevance(
        self,
        job_title: str,
        user_titles: list[str],
    ) -> float:
        """Analyze how relevant the job title is to user's experience."""
        if not user_titles:
            return 50.0  # Neutral score

        job_words = set(job_title.lower().split())

        max_overlap = 0
        for title in user_titles:
            title_words = set(title.lower().split())
            overlap = len(job_words & title_words)
            max_overlap = max(max_overlap, overlap)

        if max_overlap == 0:
            return 30.0
        elif max_overlap == 1:
            return 60.0
        elif max_overlap == 2:
            return 80.0
        else:
            return 100.0

    def _identify_strengths_gaps(
        self,
        skill_matches: list[SkillMatch],
        exp_match: ExperienceMatch | None,
    ) -> tuple[list[str], list[str]]:
        """Identify user strengths and gaps for the job."""
        strengths = []
        gaps = []

        for sm in skill_matches:
            if sm.user_has and sm.proficiency_match >= 0.75:
                strengths.append(f"Strong {sm.skill} skills")
            elif not sm.user_has and sm.required:
                gaps.append(f"Missing required skill: {sm.skill}")

        if exp_match:
            if exp_match.is_sufficient:
                strengths.append(f"Meets experience requirement ({exp_match.years_user_has}+ years)")
            elif exp_match.years_required:
                gaps.append(f"Experience gap: {exp_match.years_required - exp_match.years_user_has} years short")

        return strengths[:5], gaps[:5]

    def _generate_reasoning(
        self,
        total: float,
        skill: float,
        exp: float,
        role: float,
        strengths: list[str],
        gaps: list[str],
    ) -> str:
        """Generate human-readable match reasoning."""
        parts = []

        if total >= 80:
            parts.append("Excellent match!")
        elif total >= 60:
            parts.append("Good match.")
        else:
            parts.append("Partial match.")

        parts.append(f"Skills: {skill:.0f}%, Experience: {exp:.0f}%, Role fit: {role:.0f}%.")

        if strengths:
            parts.append(f"Strengths: {', '.join(strengths[:3])}.")
        if gaps:
            parts.append(f"Gaps: {', '.join(gaps[:3])}.")

        return " ".join(parts)
