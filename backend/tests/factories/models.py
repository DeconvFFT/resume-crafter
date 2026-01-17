"""Test factories for database models."""

from datetime import date, datetime, timezone
from uuid import uuid4

import factory
from factory import Faker, LazyAttribute, SubFactory

from src.models.database import (
    Document,
    DocumentClass,
    Experience,
    ExperienceBullet,
    JobDescription,
    JobRequirement,
    Project,
    ProjectBullet,
    RequirementType,
    ResumeMatch,
    ResumeMatchItem,
    SourceType,
    TaskStatus,
    User,
)
from src.auth.jwt import get_password_hash


class UserFactory(factory.Factory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    id = LazyAttribute(lambda _: uuid4())
    email = Faker("email")
    password_hash = LazyAttribute(lambda _: get_password_hash("password123"))
    full_name = Faker("name")
    phone = Faker("phone_number")
    location = Faker("city")
    linkedin_url = LazyAttribute(
        lambda o: f"https://linkedin.com/in/{o.full_name.lower().replace(' ', '-')}"
    )
    github_url = LazyAttribute(
        lambda o: f"https://github.com/{o.full_name.lower().replace(' ', '')}"
    )
    portfolio_url = None
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class DocumentFactory(factory.Factory):
    """Factory for creating Document instances."""

    class Meta:
        model = Document

    id = LazyAttribute(lambda _: uuid4())
    user_id = LazyAttribute(lambda _: uuid4())
    filename = Faker("file_name", extension="pdf")
    file_path = LazyAttribute(lambda o: f"/uploads/{o.user_id}/{o.filename}")
    file_size_bytes = Faker("random_int", min=10000, max=1000000)
    mime_type = "application/pdf"
    source_type = SourceType.LOCAL_FILE
    source_url = None
    document_class = None
    classification_confidence = None
    verified_by_user = False
    processing_status = TaskStatus.PENDING
    processing_error = None
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class ExperienceFactory(factory.Factory):
    """Factory for creating Experience instances."""

    class Meta:
        model = Experience

    id = LazyAttribute(lambda _: uuid4())
    user_id = LazyAttribute(lambda _: uuid4())
    company = Faker("company")
    role = Faker("job")
    location = Faker("city")
    start_date = LazyAttribute(lambda _: date(2020, 1, 1))
    end_date = LazyAttribute(lambda _: date(2023, 6, 30))
    description = Faker("paragraph")
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class ExperienceBulletFactory(factory.Factory):
    """Factory for creating ExperienceBullet instances."""

    class Meta:
        model = ExperienceBullet

    id = LazyAttribute(lambda _: uuid4())
    experience_id = LazyAttribute(lambda _: uuid4())
    content = Faker("sentence", nb_words=15)
    skills = LazyAttribute(lambda _: ["Python", "FastAPI", "PostgreSQL"])
    metrics = LazyAttribute(lambda _: ["50% improvement"])
    action_verbs = LazyAttribute(lambda _: ["Built", "Designed"])
    embedding_id = None
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class ProjectFactory(factory.Factory):
    """Factory for creating Project instances."""

    class Meta:
        model = Project

    id = LazyAttribute(lambda _: uuid4())
    user_id = LazyAttribute(lambda _: uuid4())
    name = Faker("catch_phrase")
    description = Faker("paragraph")
    technologies = LazyAttribute(lambda _: ["React", "TypeScript", "Node.js"])
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class ProjectBulletFactory(factory.Factory):
    """Factory for creating ProjectBullet instances."""

    class Meta:
        model = ProjectBullet

    id = LazyAttribute(lambda _: uuid4())
    project_id = LazyAttribute(lambda _: uuid4())
    content = Faker("sentence", nb_words=12)
    skills = LazyAttribute(lambda _: ["React", "TypeScript"])
    embedding_id = None
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class JobDescriptionFactory(factory.Factory):
    """Factory for creating JobDescription instances."""

    class Meta:
        model = JobDescription

    id = LazyAttribute(lambda _: uuid4())
    user_id = LazyAttribute(lambda _: uuid4())
    source_url = Faker("url")
    raw_text = Faker("text", max_nb_chars=2000)
    company = Faker("company")
    role = Faker("job")
    location = Faker("city")
    salary_range = "$120,000 - $150,000"
    experience_level = "senior"
    processing_status = TaskStatus.PENDING
    processing_error = None
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class JobRequirementFactory(factory.Factory):
    """Factory for creating JobRequirement instances."""

    class Meta:
        model = JobRequirement

    id = LazyAttribute(lambda _: uuid4())
    job_id = LazyAttribute(lambda _: uuid4())
    content = Faker("sentence", nb_words=10)
    requirement_type = RequirementType.TECHNICAL_SKILL
    importance_score = Faker("random_int", min=1, max=5)
    keywords = LazyAttribute(lambda _: ["Python", "AWS"])
    embedding_id = None
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class ResumeMatchFactory(factory.Factory):
    """Factory for creating ResumeMatch instances."""

    class Meta:
        model = ResumeMatch

    id = LazyAttribute(lambda _: uuid4())
    user_id = LazyAttribute(lambda _: uuid4())
    job_id = LazyAttribute(lambda _: uuid4())
    overall_match_score = Faker("pyfloat", min_value=0.5, max_value=1.0)
    skill_coverage = Faker("pyfloat", min_value=0.5, max_value=1.0)
    experience_relevance = Faker("pyfloat", min_value=0.5, max_value=1.0)
    processing_status = TaskStatus.COMPLETED
    processing_error = None
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
    updated_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class ResumeMatchItemFactory(factory.Factory):
    """Factory for creating ResumeMatchItem instances."""

    class Meta:
        model = ResumeMatchItem

    id = LazyAttribute(lambda _: uuid4())
    match_id = LazyAttribute(lambda _: uuid4())
    requirement_id = LazyAttribute(lambda _: uuid4())
    bullet_id = LazyAttribute(lambda _: uuid4())
    bullet_type = "experience"
    relevance_score = Faker("pyfloat", min_value=0.5, max_value=1.0)
    match_explanation = Faker("sentence")
    included_in_resume = True
    created_at = LazyAttribute(lambda _: datetime.now(timezone.utc))
