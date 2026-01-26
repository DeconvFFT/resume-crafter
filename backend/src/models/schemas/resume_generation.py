"""Schemas for multi-agent resume generation system."""

from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID


@dataclass
class BulletData:
    """Individual bullet point with metadata."""

    id: UUID
    content: str
    skills: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    order_index: int = 0


@dataclass
class ExperienceData:
    """Experience entry with bullets."""

    id: UUID
    company: str
    role: str
    location: str | None
    start_date: str | None
    end_date: str | None
    is_current: bool
    bullets: list[BulletData] = field(default_factory=list)


@dataclass
class ProjectData:
    """Project entry with bullets and links."""

    id: UUID
    name: str
    description: str | None
    technologies: list[str] = field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[BulletData] = field(default_factory=list)
    links: list[dict[str, str]] = field(default_factory=list)


@dataclass
class SkillData:
    """Skill with category and proficiency."""

    id: UUID
    name: str
    category: str | None = None
    proficiency: str | None = None


@dataclass
class PublicationData:
    """Publication entry."""

    id: UUID
    title: str
    authors: str | list[str] | None = None
    venue: str | None = None
    publication_date: str | None = None
    publication_type: str | None = None
    doi: str | None = None
    url: str | None = None


@dataclass
class JobRequirementData:
    """Job requirement for matching."""

    id: UUID
    content: str
    requirement_type: str
    importance_score: int = 3
    keywords: list[str] = field(default_factory=list)


@dataclass
class CollectedResumeData:
    """Output from CollectionAgent - all user data structured for processing."""

    # User profile
    profile: dict[str, Any]

    # User content
    experiences: list[ExperienceData]
    projects: list[ProjectData]
    skills: list[SkillData]
    publications: list[PublicationData]

    # Job context
    job_id: UUID
    job_company: str | None
    job_role: str | None
    job_location: str | None
    requirements: list[JobRequirementData]


@dataclass
class ScoredBullet:
    """Bullet with relevance scoring."""

    bullet: BulletData
    relevance_score: float  # 0-1
    matched_requirements: list[UUID] = field(default_factory=list)
    explanation: str | None = None


@dataclass
class ScoredExperience:
    """Experience with scored bullets."""

    experience: ExperienceData
    bullets: list[ScoredBullet]
    overall_score: float  # Average of bullet scores


@dataclass
class ScoredProject:
    """Project with scored bullets."""

    project: ProjectData
    bullets: list[ScoredBullet]
    overall_score: float


@dataclass
class ScoredSkill:
    """Skill matched to requirements."""

    skill: SkillData
    is_required: bool  # Matches a job requirement
    matched_requirement_ids: list[UUID] = field(default_factory=list)


@dataclass
class MappedResumeData:
    """Output from MappingAgent - scored and mapped content."""

    # Profile passed through
    profile: dict[str, Any]

    # Scored content
    experiences: list[ScoredExperience]
    projects: list[ScoredProject]
    skills: list[ScoredSkill]
    publications: list[PublicationData]  # Passed through

    # Job context
    job_id: UUID
    job_company: str | None
    job_role: str | None

    # Analysis
    requirement_coverage: dict[str, list[str]]  # requirement_id -> bullet contents
    skill_gaps: list[str]  # Required skills user lacks
    overall_fit_score: float  # 0-1


@dataclass
class ResumeGenerationOptions:
    """Configuration for resume generation."""

    format: Literal["json", "markdown", "google_doc"] = "json"
    max_experiences: int = 4
    max_projects: int = 3
    max_bullets_per_experience: int = 4
    max_bullets_per_project: int = 3
    template: Literal["standard", "technical", "academic"] = "standard"
    include_all_skills: bool = True
    include_publications: bool = True
    relevance_threshold: float = 0.3  # Min score to include


@dataclass
class OptimizationNote:
    """Suggestion for resume improvement."""

    category: str  # "content", "formatting", "keywords", "structure"
    message: str
    severity: str  # "info", "warning", "suggestion"


@dataclass
class GeneratedResumeResult:
    """Final output from ResumeBuilderAgent."""

    # Resume content
    json_data: dict[str, Any]
    markdown: str

    # Quality metrics
    ats_score: float  # 0-100
    keyword_density: float  # Percentage of job keywords present
    optimization_notes: list[OptimizationNote] = field(default_factory=list)

    # Metadata
    experiences_included: int = 0
    projects_included: int = 0
    skills_included: int = 0
    publications_included: int = 0


# ATS Template definitions
ATS_TEMPLATES = {
    "standard": {
        "sections": [
            "SUMMARY",
            "EXPERIENCE",
            "PROJECTS",
            "SKILLS",
            "PUBLICATIONS",
            "EDUCATION",
        ],
        "formatting": {
            "font": "Arial or Calibri",
            "body_size": "10-12pt",
            "header_size": "12-14pt",
            "margins": "0.5-1 inch",
            "bullet_char": "•",
        },
        "rules": [
            "No tables, columns, or graphics",
            "Standard section headers in CAPS",
            "Dates at end of line or right-aligned",
            "Skills as comma-separated list",
            "Contact info at top, single line preferred",
            "Action verbs at start of bullets",
            "Quantify achievements where possible",
        ],
    },
    "technical": {
        "sections": [
            "SUMMARY",
            "TECHNICAL SKILLS",
            "EXPERIENCE",
            "PROJECTS",
            "PUBLICATIONS",
            "EDUCATION",
        ],
        "formatting": {
            "font": "Arial or Calibri",
            "body_size": "10-11pt",
            "header_size": "12-14pt",
            "margins": "0.5-0.75 inch",
            "bullet_char": "•",
        },
        "rules": [
            "Lead with technical skills section",
            "Group skills by category",
            "Include GitHub/portfolio links",
            "Emphasize technologies in bullets",
            "No tables, columns, or graphics",
        ],
    },
    "academic": {
        "sections": [
            "SUMMARY",
            "EDUCATION",
            "PUBLICATIONS",
            "RESEARCH EXPERIENCE",
            "PROJECTS",
            "SKILLS",
        ],
        "formatting": {
            "font": "Times New Roman or Calibri",
            "body_size": "11-12pt",
            "header_size": "12-14pt",
            "margins": "1 inch",
            "bullet_char": "•",
        },
        "rules": [
            "Lead with education section",
            "Publications in proper citation format",
            "Emphasize research and teaching",
            "Include conference presentations",
            "No tables, columns, or graphics",
        ],
    },
}
