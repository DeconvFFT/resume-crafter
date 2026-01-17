"""Pydantic schemas for structured LLM outputs using instructor."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


def _normalize_metrics(v: Any) -> str | None:
    """Convert metrics to string format."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        # Convert dict like {"accuracy": "76%"} to string "accuracy: 76%"
        parts = [f"{k}: {val}" for k, val in v.items()]
        return ", ".join(parts)
    return str(v)


class DetectedEntities(BaseModel):
    """Entities detected during document classification."""

    companies: list[str] = Field(default_factory=list, description="Company names found")
    job_titles: list[str] = Field(default_factory=list, description="Job titles found")
    dates: list[str] = Field(default_factory=list, description="Date ranges found (e.g., 'Jan 2020 - Mar 2022')")
    skills: list[str] = Field(default_factory=list, description="Technical skills found")
    urls: list[str] = Field(default_factory=list, description="URLs found (GitHub, portfolio, etc.)")
    certifications: list[str] = Field(default_factory=list, description="Certifications mentioned")


class DocumentClassification(BaseModel):
    """LLM output schema for document classification."""

    classification: Literal["resume", "experience", "project", "supporting"]
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    reasoning: str = Field(..., description="Explanation for the classification")
    detected_entities: DetectedEntities
    has_experiences: bool = Field(default=False, description="Whether document contains work experiences")
    has_projects: bool = Field(default=False, description="Whether document contains projects")


class ExtractedExperienceBullet(BaseModel):
    """Extracted bullet point from experience document."""

    content: str = Field(..., description="The bullet point text")
    skills: list[str] = Field(default_factory=list, description="Skills demonstrated")
    metrics: str | None = Field(None, description="Quantified achievements if any")
    action_verbs: list[str] = Field(default_factory=list, description="Action verbs used")

    @field_validator("metrics", mode="before")
    @classmethod
    def normalize_metrics(cls, v):
        return _normalize_metrics(v)


class ExtractedExperience(BaseModel):
    """Extracted experience from document."""

    company: str
    role: str
    location: str | None = None
    start_date: str = Field(..., description="Start date in YYYY-MM format")
    end_date: str | None = Field(None, description="End date in YYYY-MM format, null if current")
    is_current: bool = False
    bullets: list[ExtractedExperienceBullet]


class ExperienceExtractionResult(BaseModel):
    """LLM output for experience document extraction."""

    experiences: list[ExtractedExperience]


class ExtractedProjectBullet(BaseModel):
    """Extracted bullet point from project document."""

    content: str = Field(..., description="The bullet point text")
    skills: list[str] = Field(default_factory=list, description="Technologies/skills used")
    metrics: str | None = Field(None, description="Quantified results if any")

    @field_validator("metrics", mode="before")
    @classmethod
    def normalize_metrics(cls, v):
        return _normalize_metrics(v)


class ExtractedProject(BaseModel):
    """Extracted project from document."""

    name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    start_date: str | None = Field(None, description="Start date in YYYY-MM format")
    end_date: str | None = Field(None, description="End date in YYYY-MM format")
    bullets: list[ExtractedProjectBullet]
    links: list[dict] = Field(default_factory=list, description="Links with 'url' and 'type' keys")


class ProjectExtractionResult(BaseModel):
    """LLM output for project document extraction."""

    projects: list[ExtractedProject]


class ExtractedJobRequirement(BaseModel):
    """Extracted requirement from job description."""

    content: str = Field(..., description="The requirement text")
    requirement_type: Literal["skill", "experience", "education", "certification", "soft_skill", "other"]
    importance: int = Field(ge=1, le=5, description="Importance 1-5 (5 = must have)")
    keywords: list[str] = Field(default_factory=list, description="Key terms")


class JobDescriptionExtraction(BaseModel):
    """LLM output for job description extraction."""

    company: str | None = None
    role: str | None = None
    location: str | None = None
    salary_range: str | None = None
    experience_level: Literal["entry", "junior", "mid", "senior", "lead", "principal"] | None = None
    requirements: list[ExtractedJobRequirement] = Field(
        default_factory=list,
        description="List of extracted job requirements. May be empty if extraction fails."
    )


class BulletMatchExplanation(BaseModel):
    """LLM explanation for why a bullet matches a requirement."""

    relevance_score: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(..., description="Why this bullet matches the requirement")
    matching_skills: list[str] = Field(default_factory=list, description="Skills that match")
    gaps: list[str] = Field(default_factory=list, description="Requirements not fully addressed")


class MatchRankingResult(BaseModel):
    """LLM output for re-ranking candidate matches."""

    ranked_bullets: list[dict] = Field(
        ...,
        description="List of {bullet_id, score, explanation} ordered by relevance",
    )
    overall_assessment: str = Field(..., description="Overall assessment of match quality")


# ============ Project Enrichment Schemas ============


class ProjectUnderstanding(BaseModel):
    """LLM output for understanding a GitHub project."""

    project_type: str = Field(..., description="Type of project (e.g., web app, library, CLI tool, ML model)")
    primary_purpose: str = Field(..., description="Main purpose and problem the project solves")
    key_features: list[str] = Field(default_factory=list, description="Key features and capabilities")
    technical_architecture: str | None = Field(None, description="Brief description of technical architecture")
    technologies_used: list[str] = Field(default_factory=list, description="Technologies, languages, frameworks used")
    target_users: str | None = Field(None, description="Who would use this project")
    scale_indicators: dict[str, Any] = Field(
        default_factory=dict,
        description="Indicators of project scale (users, performance metrics, etc.)"
    )
    complexity_level: Literal["simple", "moderate", "complex", "highly_complex"] = "moderate"
    unique_aspects: list[str] = Field(default_factory=list, description="What makes this project unique or impressive")


class EnrichedProjectBullet(BaseModel):
    """A resume bullet point generated from project understanding."""

    content: str = Field(..., description="The bullet point text, action-verb led")
    skills: list[str] = Field(default_factory=list, description="Skills demonstrated")
    metrics: str | None = Field(None, description="Quantified impact if available")
    impact_type: Literal["technical", "user", "business", "learning"] = "technical"
    strength_score: float = Field(ge=0.0, le=1.0, description="How strong this bullet is for a resume")


class ProjectEnrichmentResult(BaseModel):
    """LLM output for project enrichment - generating resume-ready bullets."""

    project_summary: str = Field(..., description="One-sentence summary of the project")
    enriched_bullets: list[EnrichedProjectBullet] = Field(
        ...,
        description="Resume-ready bullet points, ordered by impact",
        min_length=3,
        max_length=8,
    )
    suggested_technologies: list[str] = Field(
        default_factory=list,
        description="Technologies to highlight for this project"
    )
    suggested_title: str | None = Field(None, description="Suggested project title for resume")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in enrichment quality")


# ============ Skills Extraction Schemas ============


class ExtractedSkill(BaseModel):
    """Extracted skill from document."""

    name: str = Field(..., description="The skill name")
    category: Literal[
        "programming_language", "framework", "database", "cloud",
        "devops", "tool", "soft_skill", "methodology", "other"
    ] = "other"
    proficiency: Literal["beginner", "intermediate", "advanced", "expert"] | None = None
    years_experience: int | None = Field(None, description="Years of experience if mentioned")
    context: str | None = Field(None, description="Context where skill was mentioned")


class SkillExtractionResult(BaseModel):
    """LLM output for skill extraction from documents."""

    skills: list[ExtractedSkill] = Field(default_factory=list)


# ============ Publications Extraction Schemas ============


class ExtractedPublication(BaseModel):
    """Extracted publication from document."""

    title: str = Field(..., description="Publication title")
    authors: list[str] = Field(default_factory=list, description="List of authors")
    publication_type: Literal[
        "journal", "conference", "book", "book_chapter",
        "thesis", "patent", "preprint", "other"
    ] = "other"
    venue: str | None = Field(None, description="Journal, conference, or publisher name")
    publication_date: str | None = Field(None, description="Publication date in YYYY-MM or YYYY format")
    doi: str | None = Field(None, description="DOI identifier if available")
    url: str | None = Field(None, description="URL to publication")
    abstract: str | None = Field(None, description="Brief abstract or description")
    is_first_author: bool = False


class PublicationExtractionResult(BaseModel):
    """LLM output for publication extraction from documents."""

    publications: list[ExtractedPublication] = Field(default_factory=list)
