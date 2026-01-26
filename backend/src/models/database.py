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


class JobSource(str, enum.Enum):
    """Source where job was discovered."""

    LINKEDIN = "linkedin"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    COMPANY_WEBSITE = "company_website"
    REFERRAL = "referral"
    OTHER = "other"


class ApplicationStatus(str, enum.Enum):
    """Status of job application in pipeline."""

    DISCOVERED = "discovered"
    FILTERED = "filtered"
    QUEUED = "queued"
    RESUME_GENERATED = "resume_generated"
    APPLYING = "applying"
    APPLIED = "applied"
    VIEWED = "viewed"
    RESPONSE_RECEIVED = "response_received"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    REJECTED = "rejected"
    OFFER_RECEIVED = "offer_received"


class OutreachStatus(str, enum.Enum):
    """Status of networking outreach."""

    PENDING = "pending"
    DRAFT_READY = "draft_ready"
    SENT = "sent"
    CONNECTED = "connected"
    NO_RESPONSE = "no_response"


class CampaignStatus(str, enum.Enum):
    """Status of search campaign."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


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

    # Automation relationships
    search_campaigns: Mapped[list["SearchCampaign"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    discovered_jobs: Mapped[list["DiscoveredJob"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    job_applications: Mapped[list["JobApplication"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    company_profiles: Mapped[list["CompanyProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    company_contacts: Mapped[list["CompanyContact"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    networking_outreach: Mapped[list["NetworkingOutreach"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    automation_logs: Mapped[list["AutomationLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")


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


# ============ Search Campaign Model ============


class SearchCampaign(Base, AuditMixin):
    """User's job search campaign with targeting criteria."""

    __tablename__ = "search_campaigns"

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

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, native_enum=False),
        default=CampaignStatus.DRAFT,
        nullable=False,
    )

    # Targeting criteria
    target_roles: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    target_locations: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    target_companies: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Keywords
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    excluded_keywords: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Salary preferences
    min_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Work preferences
    remote_preference: Mapped[str | None] = mapped_column(String(50), nullable=True)  # remote/hybrid/onsite/any
    experience_level: Mapped[str | None] = mapped_column(String(50), nullable=True)  # entry/mid/senior/lead/any

    # Scheduling
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Additional configuration
    settings: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="search_campaigns")
    discovered_jobs: Mapped[list["DiscoveredJob"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    applications: Mapped[list["JobApplication"]] = relationship(back_populates="campaign")


# ============ Discovered Job Model ============


class DiscoveredJob(Base, AuditMixin):
    """Jobs found by discovery agent."""

    __tablename__ = "discovered_jobs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("search_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # External identification
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[JobSource] = mapped_column(
        Enum(JobSource, native_enum=False),
        nullable=False,
    )

    # Job details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Salary information
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # URL and timing
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Match analysis
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    match_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_qualified: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)

    # Raw data storage
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    campaign: Mapped["SearchCampaign"] = relationship(back_populates="discovered_jobs")
    user: Mapped["User"] = relationship(back_populates="discovered_jobs")
    application: Mapped["JobApplication | None"] = relationship(back_populates="discovered_job")

    __table_args__ = (
        Index("ix_discovered_jobs_user_source_external", "user_id", "source", "external_id"),
        Index("ix_discovered_jobs_campaign_score", "campaign_id", "match_score"),
    )


# ============ Job Application Model ============


class JobApplication(Base, AuditMixin):
    """Application tracking with full pipeline."""

    __tablename__ = "job_applications"

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
    discovered_job_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("discovered_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("search_campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status tracking
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False),
        default=ApplicationStatus.DISCOVERED,
        nullable=False,
    )
    status_history: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)  # Array of {status, timestamp, notes}

    # Job details (denormalized for quick access)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    job_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Application materials
    resume_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timeline tracking
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interview_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Notes and feedback
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="job_applications")
    discovered_job: Mapped["DiscoveredJob | None"] = relationship(back_populates="application")
    campaign: Mapped["SearchCampaign | None"] = relationship(back_populates="applications")
    resume: Mapped["Document | None"] = relationship()
    outreach_messages: Mapped[list["NetworkingOutreach"]] = relationship(back_populates="application")

    __table_args__ = (
        Index("ix_job_applications_user_status", "user_id", "status"),
        Index("ix_job_applications_user_company", "user_id", "company"),
    )


# ============ Company Profile Model ============


class CompanyProfile(Base, AuditMixin):
    """Company research for networking."""

    __tablename__ = "company_profiles"

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

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Company links
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    careers_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Company details
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_stack: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Research notes
    culture_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    interview_process: Mapped[str | None] = mapped_column(Text, nullable=True)
    glassdoor_rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Additional research data
    research_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="company_profiles")
    contacts: Mapped[list["CompanyContact"]] = relationship(back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_company_profiles_user_name", "user_id", "name"),
    )


# ============ Company Contact Model ============


class CompanyContact(Base, AuditMixin):
    """People at target companies."""

    __tablename__ = "company_contacts"

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
    company_profile_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("company_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Contact details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    linkedin_url: Mapped[str] = mapped_column(String(512), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relevance scoring (hiring manager > recruiter > engineer)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="company_contacts")
    company: Mapped["CompanyProfile"] = relationship(back_populates="contacts")
    outreach_messages: Mapped[list["NetworkingOutreach"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


# ============ Networking Outreach Model ============


class NetworkingOutreach(Base, AuditMixin):
    """Email/LinkedIn drafts (NOT auto-sent)."""

    __tablename__ = "networking_outreach"

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
    contact_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("company_contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    application_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("job_applications.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Channel and status
    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # linkedin/email
    status: Mapped[OutreachStatus] = mapped_column(
        Enum(OutreachStatus, native_enum=False),
        default=OutreachStatus.PENDING,
        nullable=False,
    )

    # Message content
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)  # For email
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Timeline tracking
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Follow-up tracking
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="networking_outreach")
    contact: Mapped["CompanyContact"] = relationship(back_populates="outreach_messages")
    application: Mapped["JobApplication | None"] = relationship(back_populates="outreach_messages")

    __table_args__ = (
        Index("ix_networking_outreach_user_status", "user_id", "status"),
        Index("ix_networking_outreach_contact", "contact_id"),
    )


# ============ Automation Log Model ============


class AutomationLog(Base, AuditMixin):
    """Audit trail for all automation actions."""

    __tablename__ = "automation_logs"

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

    # Action classification
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)  # job_discovery, job_analysis, resume_generation, etc.
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)  # campaign, job, application, contact, outreach
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # started, completed, failed

    # Details and performance
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # Input/output data, error messages
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="automation_logs")

    __table_args__ = (
        Index("ix_automation_logs_user_action", "user_id", "action_type"),
        Index("ix_automation_logs_user_created", "user_id", "created_at"),
    )
