"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.main import app
from src.models.database import Base, User
from src.storage.database import get_db
from src.auth.dependencies import get_current_user
from src.auth.jwt import create_access_token


# ============================================================================
# Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def override_get_db(db_session: AsyncSession):
    """Override the get_db dependency."""
    async def _override_get_db():
        yield db_session

    return _override_get_db


# ============================================================================
# User Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from src.auth.jwt import get_password_hash

    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Create a JWT token for the test user."""
    return create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )


@pytest.fixture
def auth_headers(test_user_token: str) -> dict[str, str]:
    """Create authentication headers."""
    return {"Authorization": f"Bearer {test_user_token}"}


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def client(
    override_get_db,
    test_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def unauthenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an unauthenticated test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    mock = MagicMock()
    mock.classify_document = AsyncMock(return_value=MagicMock(
        classification="experience",
        confidence=0.95,
        reasoning="Contains employment history",
        detected_entities=MagicMock(
            companies=["Acme Corp"],
            roles=["Software Engineer"],
            dates=["2020-01", "2023-06"],
        ),
    ))
    mock.extract_experience = AsyncMock(return_value=MagicMock(
        company="Acme Corp",
        role="Software Engineer",
        start_date="2020-01-01",
        end_date="2023-06-30",
        location="San Francisco, CA",
        bullets=[
            MagicMock(
                content="Built scalable microservices",
                skills=["Python", "Docker", "Kubernetes"],
                metrics=["50% performance improvement"],
                action_verbs=["Built"],
            )
        ],
    ))
    mock.extract_job_requirements = AsyncMock(return_value=MagicMock(
        company="Tech Startup",
        role="Senior Developer",
        location="Remote",
        salary_range="$150k - $180k",
        experience_level="senior",
        requirements=[
            MagicMock(
                content="5+ years of Python experience",
                requirement_type="technical_skill",
                importance=5,
                keywords=["Python"],
            ),
            MagicMock(
                content="Experience with cloud platforms",
                requirement_type="technical_skill",
                importance=4,
                keywords=["AWS", "GCP", "Azure"],
            ),
        ],
    ))
    return mock


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    mock = MagicMock()
    mock.embed_single = AsyncMock(return_value=[0.1] * 384)
    mock.embed_batch = AsyncMock(return_value=[[0.1] * 384, [0.2] * 384])
    return mock


@pytest.fixture
def mock_arq_redis():
    """Mock ARQ Redis for testing background tasks."""
    mock = AsyncMock()
    mock.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test-job-id"))
    mock.close = AsyncMock()
    return mock


# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def sample_pdf_content() -> bytes:
    """Create sample PDF content for testing."""
    # Minimal valid PDF
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Resume) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""


@pytest.fixture
def sample_resume_text() -> str:
    """Sample resume text for testing."""
    return """
John Doe
Software Engineer
john.doe@email.com | (555) 123-4567 | San Francisco, CA

EXPERIENCE

Senior Software Engineer
Acme Corporation | Jan 2020 - Present | San Francisco, CA
- Designed and implemented microservices architecture serving 1M+ daily users
- Led migration from monolith to containerized services, reducing deployment time by 80%
- Mentored 3 junior developers and conducted technical interviews

Software Engineer
StartupXYZ | Jun 2017 - Dec 2019 | New York, NY
- Built real-time data pipeline processing 100K events/second using Apache Kafka
- Developed RESTful APIs using Python/FastAPI with 99.9% uptime
- Implemented CI/CD pipelines reducing release cycle from 2 weeks to 2 days

EDUCATION

Bachelor of Science in Computer Science
Stanford University | 2017

SKILLS
Python, JavaScript, TypeScript, Go, Docker, Kubernetes, AWS, PostgreSQL, Redis
"""


@pytest.fixture
def sample_job_description() -> str:
    """Sample job description for testing."""
    return """
Senior Software Engineer - Backend

About the Role:
We're looking for an experienced backend engineer to join our growing team.

Requirements:
- 5+ years of professional software development experience
- Strong proficiency in Python and/or Go
- Experience with cloud platforms (AWS, GCP, or Azure)
- Knowledge of containerization (Docker, Kubernetes)
- Experience with SQL and NoSQL databases
- Excellent communication skills
- BS/MS in Computer Science or equivalent

Nice to have:
- Experience with real-time data processing
- Knowledge of machine learning
- Open source contributions

Location: Remote (US)
Salary: $150,000 - $180,000 + equity

About Us:
Tech Startup is building the future of...
"""
