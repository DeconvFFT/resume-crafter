"""SQLAlchemy ORM models for Resume Crafter."""

import enum
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    type_annotation_map = {
        dict[str, Any]: JSONB,
        list[str]: ARRAY(String),
    }


class AuditMixin:
    """Mixin providing audit fields for all models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


# ============ Enums ============


class SourceType(str, enum.Enum):
    """Source of uploaded document."""

    LOCAL_FILE = "local_file"
    GOOGLE_DOC = "google_doc"
    URL = "url"


class DocumentClass(str, enum.Enum):
    """Classification of document content."""

    RESUME = "resume"  # Contains both experiences AND projects
    EXPERIENCE = "experience"  # Work experience only
    PROJECT = "project"  # Projects only
    SUPPORTING = "supporting"  # Supporting documents (certs, papers, etc.)


class SupportingDocType(str, enum.Enum):
    """Type of supporting document."""

    PAPER = "paper"
    CERTIFICATION = "certification"
    RECOMMENDATION = "recommendation"
    PORTFOLIO = "portfolio"
    OTHER = "other"


class LinkType(str, enum.Enum):
    """Type of project link."""

    GITHUB = "github"
    DEMO = "demo"
    PAPER = "paper"
    DOCS = "docs"
    VIDEO = "video"
    OTHER = "other"


class RequirementType(str, enum.Enum):
    """Type of job requirement."""

    SKILL = "skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    SOFT_SKILL = "soft_skill"
    OTHER = "other"


class SkillCategory(str, enum.Enum):
    """Category of skill."""

    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD = "cloud"
    DEVOPS = "devops"
    TOOL = "tool"
    SOFT_SKILL = "soft_skill"
    METHODOLOGY = "methodology"
    OTHER = "other"


class ProficiencyLevel(str, enum.Enum):
    """Proficiency level for skills."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class PublicationType(str, enum.Enum):
    """Type of publication."""

    JOURNAL = "journal"
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    PREPRINT = "preprint"
    THESIS = "thesis"
    BOOK_CHAPTER = "book_chapter"
    PATENT = "patent"
    OTHER = "other"


class TaskStatus(str, enum.Enum):
    """Status of background task."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============ User Model ============


class User(Base, AuditMixin):
    """User account with profile information."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile fields
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    websites: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    experiences: Mapped[list["Experience"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    skills: Mapped[list["Skill"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    publications: Mapped[list["Publication"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    job_descriptions: Mapped[list["JobDescription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    resume_matches: Mapped[list["ResumeMatch"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# ============ Document Model ============


class Document(Base, AuditMixin):
    """Uploaded document with classification metadata."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Extracted content
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Classification
    document_class: Mapped[DocumentClass | None] = mapped_column(
        Enum(DocumentClass, native_enum=False),
        nullable=True,
    )
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    classification_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Processing status
    processing_status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Processing logs for showing LLM chain-of-thought
    processing_logs: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True, default=list)

    # Checkpoint state for resumable processing
    checkpoint_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    checkpoint_step: Mapped[str | None] = mapped_column(String(50), nullable=True)
    checkpoint_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processing_attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="documents")

    __table_args__ = (
        Index("ix_documents_user_class", "user_id", "document_class"),
    )


# ============ Experience Models ============


class Experience(Base, AuditMixin):
    """Work experience entry."""

    __tablename__ = "experiences"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    company: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date | None] = mapped_column(nullable=True)  # None = current
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="experiences")
    bullets: Mapped[list["ExperienceBullet"]] = relationship(
        back_populates="experience",
        cascade="all, delete-orphan",
        order_by="ExperienceBullet.order_index",
    )
    supporting_documents: Mapped[list["SupportingDocument"]] = relationship(
        back_populates="experience",
        cascade="all, delete-orphan",
    )


class ExperienceBullet(Base, AuditMixin):
    """Individual bullet point for an experience."""

    __tablename__ = "experience_bullets"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    experience_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("experiences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Extracted metadata
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g., "increased by 50%"
    action_verbs: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Vector embedding reference
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    experience: Mapped["Experience"] = relationship(back_populates="bullets")


# ============ Project Models ============


class Project(Base, AuditMixin):
    """Project entry."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technologies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    start_date: Mapped[date | None] = mapped_column(nullable=True)
    end_date: Mapped[date | None] = mapped_column(nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="projects")
    bullets: Mapped[list["ProjectBullet"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectBullet.order_index",
    )
    links: Mapped[list["ProjectLink"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    supporting_documents: Mapped[list["SupportingDocument"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectBullet(Base, AuditMixin):
    """Individual bullet point for a project."""

    __tablename__ = "project_bullets"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Extracted metadata
    skills: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vector embedding reference
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="bullets")


class ProjectLink(Base, AuditMixin):
    """Link associated with a project."""

    __tablename__ = "project_links"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    project_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    link_type: Mapped[LinkType] = mapped_column(
        Enum(LinkType, native_enum=False),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="links")


# ============ Skill Model ============


class Skill(Base, AuditMixin):
    """User skill with proficiency and categorization."""

    __tablename__ = "skills"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[SkillCategory] = mapped_column(
        Enum(SkillCategory, native_enum=False),
        default=SkillCategory.OTHER,
        nullable=False,
    )
    proficiency: Mapped[ProficiencyLevel | None] = mapped_column(
        Enum(ProficiencyLevel, native_enum=False),
        nullable=True,
    )
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_highlighted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Vector embedding reference for matching
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="skills")

    __table_args__ = (
        Index("ix_skills_user_category", "user_id", "category"),
    )


# ============ Publication Model ============


class Publication(Base, AuditMixin):
    """Academic publication or research paper."""

    __tablename__ = "publications"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    authors: Mapped[str] = mapped_column(Text, nullable=False)  # Comma-separated or formatted
    publication_type: Mapped[PublicationType] = mapped_column(
        Enum(PublicationType, native_enum=False),
        default=PublicationType.OTHER,
        nullable=False,
    )

    # Venue information
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Journal/conference name
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Date and identifiers
    publication_date: Mapped[date | None] = mapped_column(nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Content
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # User's role
    is_first_author: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    author_position: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-indexed

    # Display
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Vector embedding for matching
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="publications")

    __table_args__ = (
        Index("ix_publications_user_type", "user_id", "publication_type"),
    )


# ============ Supporting Document Model ============


class SupportingDocument(Base, AuditMixin):
    """Supporting document linked to experience or project."""

    __tablename__ = "supporting_documents"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Parent entity (either experience or project)
    experience_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("experiences.id", ondelete="CASCADE"),
        nullable=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )

    doc_type: Mapped[SupportingDocType] = mapped_column(
        Enum(SupportingDocType, native_enum=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Type-specific fields
    # Paper
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    doi_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Certification
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(nullable=True)
    credential_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    credential_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Recommendation
    recommender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recommender_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recommender_relationship: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Portfolio
    portfolio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Relationships
    experience: Mapped["Experience | None"] = relationship(back_populates="supporting_documents")
    project: Mapped["Project | None"] = relationship(back_populates="supporting_documents")

    __table_args__ = (
        CheckConstraint(
            "(experience_id IS NOT NULL AND project_id IS NULL) OR "
            "(experience_id IS NULL AND project_id IS NOT NULL)",
            name="ck_supporting_docs_parent",
        ),
    )


# ============ Job Description Models ============


class JobDescription(Base, AuditMixin):
    """Analyzed job description."""

    __tablename__ = "job_descriptions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Extracted fields
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)  # junior, mid, senior

    # Processing status
    processing_status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="job_descriptions")
    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobRequirement.importance_score.desc()",
    )


class JobRequirement(Base, AuditMixin):
    """Individual requirement from a job description."""

    __tablename__ = "job_requirements"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[RequirementType] = mapped_column(
        Enum(RequirementType, native_enum=False),
        nullable=False,
    )
    importance_score: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1-5
    keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Vector embedding reference
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    job: Mapped["JobDescription"] = relationship(back_populates="requirements")

    __table_args__ = (
        CheckConstraint("importance_score >= 1 AND importance_score <= 5", name="ck_importance_range"),
    )


# ============ Resume Match Models ============


class ResumeMatch(Base, AuditMixin):
    """Match results for a user against a job description."""

    __tablename__ = "resume_matches"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scores
    overall_match_score: Mapped[float] = mapped_column(Float, nullable=False)
    skill_coverage: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1
    experience_relevance: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1

    # Processing status
    processing_status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        default=TaskStatus.PENDING,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="resume_matches")
    job: Mapped["JobDescription"] = relationship()
    items: Mapped[list["ResumeMatchItem"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
        order_by="ResumeMatchItem.relevance_score.desc()",
    )

    __table_args__ = (
        Index("ix_resume_matches_user_job", "user_id", "job_id"),
    )


class ResumeMatchItem(Base, AuditMixin):
    """Individual match item linking a bullet to a requirement."""

    __tablename__ = "resume_match_items"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    match_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("resume_matches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requirement_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Matched bullet (either experience or project)
    experience_bullet_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("experience_bullets.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_bullet_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("project_bullets.id", ondelete="SET NULL"),
        nullable=True,
    )

    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    included_in_resume: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    match: Mapped["ResumeMatch"] = relationship(back_populates="items")
    requirement: Mapped["JobRequirement"] = relationship()
    experience_bullet: Mapped["ExperienceBullet | None"] = relationship()
    project_bullet: Mapped["ProjectBullet | None"] = relationship()


# ============ Background Task Tracking ============


class BackgroundTask(Base, AuditMixin):
    """Track background task status for frontend polling."""

    __tablename__ = "background_tasks"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    task_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "process_document"
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0-100
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_background_tasks_user_status", "user_id", "status"),
    )
