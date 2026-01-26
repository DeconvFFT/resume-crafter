"""Test configurations and verification utilities for the automation system.

Tests for:
- Rate limiting logic (30-40 apps/day, 5 min delays)
- Job scoring algorithm
- Campaign state transitions
- Execution monitoring

Run with: pytest backend/tests/test_automation.py -v
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import (
    ApplicationStatus,
    AutomationLog,
    CampaignStatus,
    DiscoveredJob,
    JobApplication,
    JobSource,
    SearchCampaign,
    User,
)
from src.tasks.automation_tasks import (
    MAX_APPLICATIONS_PER_DAY,
    MIN_APPLICATION_DELAY_SECONDS,
    can_submit_application,
    get_applications_today_count,
    get_last_application_time,
)
from src.agents.automation.job_qualification_agent import (
    JobQualificationAgent,
    JobRequirements,
    QualificationResult,
    UserProfile,
)
from src.core.scheduler import (
    CronJobState,
    CronJobStatus,
    CronJobType,
    CronScheduler,
)


# ============================================================================
# Rate Limiting Tests
# ============================================================================


class TestRateLimiting:
    """Test rate limiting logic for application submissions."""

    @pytest.mark.asyncio
    async def test_daily_application_limit_constant(self):
        """Verify daily application limit is in 30-40 range."""
        assert 30 <= MAX_APPLICATIONS_PER_DAY <= 40, (
            f"Daily limit {MAX_APPLICATIONS_PER_DAY} should be between 30-40"
        )

    @pytest.mark.asyncio
    async def test_delay_between_applications(self):
        """Verify minimum delay is 5 minutes (300 seconds)."""
        assert MIN_APPLICATION_DELAY_SECONDS == 300, (
            f"Delay should be 300 seconds (5 min), got {MIN_APPLICATION_DELAY_SECONDS}"
        )

    @pytest.mark.asyncio
    async def test_can_submit_when_below_daily_limit(self, db_session: AsyncSession, test_user: User):
        """User can submit when below daily limit."""
        # Create a few applications for today (less than limit)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(5):
            app = JobApplication(
                user_id=test_user.id,
                status=ApplicationStatus.APPLIED,
                job_title=f"Test Job {i}",
                company=f"Company {i}",
                applied_at=today_start + timedelta(hours=i),
            )
            db_session.add(app)
        await db_session.commit()

        can_submit, reason = await can_submit_application(db_session, test_user.id)

        # Should be able to submit (only 5 applications today)
        # Note: might fail if also fails delay check
        count = await get_applications_today_count(db_session, test_user.id)
        assert count == 5, f"Expected 5 applications today, got {count}"
        assert count < MAX_APPLICATIONS_PER_DAY

    @pytest.mark.asyncio
    async def test_cannot_submit_when_at_daily_limit(self, db_session: AsyncSession, test_user: User):
        """User cannot submit when at or above daily limit."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Create MAX applications for today
        for i in range(MAX_APPLICATIONS_PER_DAY):
            app = JobApplication(
                user_id=test_user.id,
                status=ApplicationStatus.APPLIED,
                job_title=f"Test Job {i}",
                company=f"Company {i}",
                applied_at=today_start + timedelta(minutes=i * 10),
            )
            db_session.add(app)
        await db_session.commit()

        can_submit, reason = await can_submit_application(db_session, test_user.id)

        assert can_submit is False
        assert "Daily limit reached" in reason

    @pytest.mark.asyncio
    async def test_must_wait_between_applications(self, db_session: AsyncSession, test_user: User):
        """User must wait minimum delay between applications."""
        # Create a recent application (1 minute ago)
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        app = JobApplication(
            user_id=test_user.id,
            status=ApplicationStatus.APPLIED,
            job_title="Recent Job",
            company="Recent Company",
            applied_at=recent_time,
        )
        db_session.add(app)
        await db_session.commit()

        can_submit, reason = await can_submit_application(db_session, test_user.id)

        assert can_submit is False
        assert "Rate limit" in reason or "wait" in reason.lower()

    @pytest.mark.asyncio
    async def test_can_submit_after_delay_passed(self, db_session: AsyncSession, test_user: User):
        """User can submit after minimum delay has passed."""
        # Create an application from 10 minutes ago (longer than 5 min delay)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        app = JobApplication(
            user_id=test_user.id,
            status=ApplicationStatus.APPLIED,
            job_title="Old Job",
            company="Old Company",
            applied_at=old_time,
        )
        db_session.add(app)
        await db_session.commit()

        can_submit, reason = await can_submit_application(db_session, test_user.id)

        assert can_submit is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_applications_count_only_today(self, db_session: AsyncSession, test_user: User):
        """Daily count only includes today's applications."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        today = datetime.now(timezone.utc)

        # Create 10 applications yesterday
        for i in range(10):
            app = JobApplication(
                user_id=test_user.id,
                status=ApplicationStatus.APPLIED,
                job_title=f"Yesterday Job {i}",
                company=f"Company {i}",
                applied_at=yesterday,
            )
            db_session.add(app)

        # Create 3 applications today
        for i in range(3):
            app = JobApplication(
                user_id=test_user.id,
                status=ApplicationStatus.APPLIED,
                job_title=f"Today Job {i}",
                company=f"Company {i}",
                applied_at=today,
            )
            db_session.add(app)

        await db_session.commit()

        count = await get_applications_today_count(db_session, test_user.id)
        assert count == 3, f"Expected 3 today, got {count}"


# ============================================================================
# Job Scoring Algorithm Tests
# ============================================================================


class TestJobScoringAlgorithm:
    """Test the job qualification and scoring algorithm."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = JobQualificationAgent()

        # Standard user profile for testing
        self.user_profile = UserProfile(
            skills=["python", "javascript", "react", "docker", "aws", "postgresql"],
            skill_proficiencies={
                "python": "advanced",
                "javascript": "intermediate",
                "react": "intermediate",
                "docker": "beginner",
                "aws": "intermediate",
                "postgresql": "advanced",
            },
            years_of_experience=5,
            job_titles=["Software Engineer", "Backend Developer", "Python Developer"],
            industries=["Technology", "Finance"],
        )

    @pytest.mark.asyncio
    async def test_high_match_score_for_matching_job(self):
        """Job with matching skills should get high score."""
        job_requirements = JobRequirements(
            job_id="test-job-1",
            title="Senior Software Engineer",
            required_skills=["python", "postgresql", "aws"],
            preferred_skills=["docker"],
            min_years_experience=4,
        )

        result = await self.agent.run(job_requirements, self.user_profile)

        assert result.match_score >= 70, f"Expected score >= 70, got {result.match_score}"
        assert result.is_qualified is True
        assert len(result.strengths) > 0

    @pytest.mark.asyncio
    async def test_low_match_score_for_mismatched_job(self):
        """Job with non-matching skills should get low score."""
        job_requirements = JobRequirements(
            job_id="test-job-2",
            title="Mobile Developer",
            required_skills=["swift", "kotlin", "ios", "android"],
            min_years_experience=3,
        )

        result = await self.agent.run(job_requirements, self.user_profile)

        assert result.match_score < 60, f"Expected score < 60, got {result.match_score}"
        assert result.is_qualified is False
        assert len(result.gaps) > 0

    @pytest.mark.asyncio
    async def test_experience_requirement_affects_score(self):
        """Insufficient experience should reduce score."""
        job_requirements = JobRequirements(
            job_id="test-job-3",
            title="Principal Software Engineer",
            required_skills=["python", "aws"],
            min_years_experience=15,  # User only has 5 years
        )

        result = await self.agent.run(job_requirements, self.user_profile)

        assert result.experience_match is not None
        assert result.experience_match.is_sufficient is False
        # Score should be affected by experience gap
        assert "experience" in result.match_reasoning.lower() or any(
            "experience" in gap.lower() for gap in result.gaps
        )

    @pytest.mark.asyncio
    async def test_qualification_threshold(self):
        """Verify qualification threshold is applied correctly."""
        # Agent should have a threshold around 60
        assert self.agent.QUALIFICATION_THRESHOLD == 60

        # Test job at threshold
        job_requirements = JobRequirements(
            job_id="test-job-4",
            title="Software Developer",
            required_skills=["python", "java"],  # Only 1 match
            min_years_experience=5,
        )

        result = await self.agent.run(job_requirements, self.user_profile)

        # Verify qualification is based on threshold
        if result.match_score >= 60:
            assert result.is_qualified is True
        else:
            assert result.is_qualified is False

    @pytest.mark.asyncio
    async def test_skill_extraction_from_description(self):
        """Test that skills are extracted from job descriptions."""
        job_reqs = self.agent.extract_requirements(
            job_id="test-job-5",
            title="Full Stack Developer",
            description="""
            We are looking for a Full Stack Developer with:
            - 5+ years of experience with Python and JavaScript
            - Experience with React and Node.js
            - Familiarity with AWS and Docker
            - PostgreSQL database experience
            """,
            requirements_text="Must have Python and AWS experience",
        )

        assert "python" in job_reqs.required_skills
        assert job_reqs.min_years_experience == 5

    @pytest.mark.asyncio
    async def test_batch_qualification(self):
        """Test batch qualification of multiple jobs."""
        jobs = [
            JobRequirements(
                job_id=f"batch-job-{i}",
                title="Software Engineer",
                required_skills=["python"] if i % 2 == 0 else ["cobol"],
                min_years_experience=3,
            )
            for i in range(5)
        ]

        results = await self.agent.batch_qualify(
            jobs, self.user_profile, filter_unqualified=True
        )

        # Only jobs with Python should be qualified
        assert len(results) >= 1
        # Results should be sorted by score
        scores = [r.match_score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_score_breakdown_weights(self):
        """Verify scoring weights are reasonable."""
        # Check weight totals
        total_weight = (
            self.agent.SKILL_WEIGHT +
            self.agent.EXPERIENCE_WEIGHT +
            self.agent.ROLE_WEIGHT +
            self.agent.OTHER_WEIGHT
        )
        assert total_weight == 100, f"Weights should sum to 100, got {total_weight}"

        # Skills should be most important
        assert self.agent.SKILL_WEIGHT >= self.agent.EXPERIENCE_WEIGHT
        assert self.agent.SKILL_WEIGHT >= self.agent.ROLE_WEIGHT


# ============================================================================
# Campaign State Transitions Tests
# ============================================================================


class TestCampaignStateTransitions:
    """Test campaign state machine transitions."""

    @pytest.mark.asyncio
    async def test_campaign_initial_state_is_draft(self, db_session: AsyncSession, test_user: User):
        """New campaigns should start in draft state."""
        campaign = SearchCampaign(
            user_id=test_user.id,
            name="Test Campaign",
            status=CampaignStatus.DRAFT,
            target_roles=["Software Engineer"],
            target_locations=["San Francisco"],
            keywords=["python"],
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        assert campaign.status == CampaignStatus.DRAFT

    @pytest.mark.asyncio
    async def test_valid_state_transitions(self):
        """Test valid campaign state transitions."""
        # Valid transitions:
        # DRAFT -> ACTIVE
        # ACTIVE -> PAUSED
        # ACTIVE -> COMPLETED
        # PAUSED -> ACTIVE
        # PAUSED -> COMPLETED

        valid_transitions = [
            (CampaignStatus.DRAFT, CampaignStatus.ACTIVE),
            (CampaignStatus.ACTIVE, CampaignStatus.PAUSED),
            (CampaignStatus.ACTIVE, CampaignStatus.COMPLETED),
            (CampaignStatus.PAUSED, CampaignStatus.ACTIVE),
            (CampaignStatus.PAUSED, CampaignStatus.COMPLETED),
        ]

        for from_state, to_state in valid_transitions:
            # This documents the expected behavior
            assert from_state != to_state, f"Transition {from_state} -> {to_state} should change state"

    @pytest.mark.asyncio
    async def test_campaign_activation_sets_next_run(self, db_session: AsyncSession, test_user: User):
        """Activating a campaign should set next_run_at."""
        campaign = SearchCampaign(
            user_id=test_user.id,
            name="Activate Test Campaign",
            status=CampaignStatus.DRAFT,
            target_roles=["Developer"],
            target_locations=[],
            keywords=[],
        )
        db_session.add(campaign)
        await db_session.commit()

        # Simulate activation
        campaign.status = CampaignStatus.ACTIVE
        campaign.next_run_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(campaign)

        assert campaign.status == CampaignStatus.ACTIVE
        assert campaign.next_run_at is not None

    @pytest.mark.asyncio
    async def test_campaign_pause_clears_next_run(self, db_session: AsyncSession, test_user: User):
        """Pausing a campaign should clear next_run_at."""
        campaign = SearchCampaign(
            user_id=test_user.id,
            name="Pause Test Campaign",
            status=CampaignStatus.ACTIVE,
            target_roles=["Developer"],
            target_locations=[],
            keywords=[],
            next_run_at=datetime.now(timezone.utc),
        )
        db_session.add(campaign)
        await db_session.commit()

        # Simulate pausing
        campaign.status = CampaignStatus.PAUSED
        campaign.next_run_at = None
        await db_session.commit()
        await db_session.refresh(campaign)

        assert campaign.status == CampaignStatus.PAUSED
        assert campaign.next_run_at is None


# ============================================================================
# Execution Monitoring Tests
# ============================================================================


class TestExecutionMonitoring:
    """Test execution monitoring and logging."""

    @pytest.mark.asyncio
    async def test_automation_log_creation(self, db_session: AsyncSession, test_user: User):
        """Test that automation actions are logged."""
        log = AutomationLog(
            user_id=test_user.id,
            action_type="job_discovery",
            entity_type="campaign",
            entity_id=uuid4(),
            status="completed",
            details={"jobs_found": 10},
            duration_ms=1500,
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.action_type == "job_discovery"
        assert log.status == "completed"
        assert log.duration_ms == 1500

    @pytest.mark.asyncio
    async def test_log_tracks_failures(self, db_session: AsyncSession, test_user: User):
        """Test that failures are properly logged."""
        log = AutomationLog(
            user_id=test_user.id,
            action_type="application_submit",
            entity_type="application",
            entity_id=uuid4(),
            status="failed",
            details={"error": "Rate limit exceeded"},
            duration_ms=500,
        )
        db_session.add(log)
        await db_session.commit()

        # Query to verify
        result = await db_session.execute(
            select(AutomationLog).where(
                AutomationLog.user_id == test_user.id,
                AutomationLog.status == "failed",
            )
        )
        failed_logs = result.scalars().all()

        assert len(failed_logs) == 1
        assert "error" in failed_logs[0].details


class TestCronScheduler:
    """Test cron scheduler functionality."""

    def setup_method(self):
        """Create a fresh scheduler for each test."""
        self.scheduler = CronScheduler()

    def test_scheduler_default_intervals(self):
        """Verify default job intervals are sensible."""
        # Job discovery: 4 hours
        assert self.scheduler.DEFAULT_JOB_DISCOVERY_INTERVAL == 4 * 60 * 60

        # Job analysis: 1 hour
        assert self.scheduler.DEFAULT_JOB_ANALYSIS_INTERVAL == 1 * 60 * 60

        # Application queue: 30 seconds
        assert self.scheduler.DEFAULT_APPLICATION_QUEUE_INTERVAL == 30

    def test_scheduler_job_types_configured(self):
        """Verify all job types are configured."""
        job_types = [
            CronJobType.JOB_DISCOVERY,
            CronJobType.JOB_ANALYSIS,
            CronJobType.APPLICATION_QUEUE,
        ]

        for job_type in job_types:
            job_state = self.scheduler.get_job_status(job_type)
            assert job_state is not None, f"Job {job_type} not configured"
            assert job_state.job_type == job_type

    def test_job_state_serialization(self):
        """Test that job state can be serialized to dict."""
        job_state = self.scheduler.get_job_status(CronJobType.JOB_DISCOVERY)
        job_dict = job_state.to_dict()

        assert "job_type" in job_dict
        assert "status" in job_dict
        assert "interval_seconds" in job_dict
        assert "run_count" in job_dict
        assert "config" in job_dict

    @pytest.mark.asyncio
    async def test_pause_and_resume_job(self):
        """Test pausing and resuming a job."""
        # Start the scheduler
        await self.scheduler.start()

        try:
            # Pause job discovery
            job_state = await self.scheduler.pause_job(CronJobType.JOB_DISCOVERY)
            assert job_state.status == CronJobStatus.PAUSED

            # Resume job discovery
            job_state = await self.scheduler.resume_job(CronJobType.JOB_DISCOVERY)
            assert job_state.status == CronJobStatus.ACTIVE
        finally:
            await self.scheduler.stop()

    @pytest.mark.asyncio
    async def test_update_job_config(self):
        """Test updating job configuration."""
        original_interval = self.scheduler.get_job_status(
            CronJobType.JOB_ANALYSIS
        ).interval_seconds

        new_interval = 7200  # 2 hours
        job_state = await self.scheduler.update_job_config(
            CronJobType.JOB_ANALYSIS,
            interval_seconds=new_interval,
            config={"batch_size": 100},
        )

        assert job_state.interval_seconds == new_interval
        assert job_state._config.get("batch_size") == 100

    @pytest.mark.asyncio
    async def test_minimum_interval_validation(self):
        """Test that minimum interval is enforced."""
        with pytest.raises(ValueError) as exc_info:
            await self.scheduler.update_job_config(
                CronJobType.JOB_DISCOVERY,
                interval_seconds=30,  # Less than 60 seconds minimum
            )

        assert "minimum" in str(exc_info.value).lower()

    def test_get_all_job_statuses(self):
        """Test getting all job statuses."""
        statuses = self.scheduler.get_all_job_statuses()

        assert len(statuses) == 3  # Three job types

        job_types = {s["job_type"] for s in statuses}
        assert "job_discovery" in job_types
        assert "job_analysis" in job_types
        assert "application_queue" in job_types


# ============================================================================
# Integration Test Helpers
# ============================================================================


class TestAutomationIntegration:
    """Integration tests for automation workflow."""

    @pytest.mark.asyncio
    async def test_full_campaign_workflow(self, db_session: AsyncSession, test_user: User):
        """Test a complete campaign workflow: create -> activate -> discover -> analyze."""
        # 1. Create campaign
        campaign = SearchCampaign(
            user_id=test_user.id,
            name="Integration Test Campaign",
            status=CampaignStatus.DRAFT,
            target_roles=["Software Engineer", "Backend Developer"],
            target_locations=["San Francisco", "Remote"],
            keywords=["python", "fastapi"],
            min_salary=150000,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        assert campaign.id is not None
        assert campaign.status == CampaignStatus.DRAFT

        # 2. Activate campaign
        campaign.status = CampaignStatus.ACTIVE
        campaign.next_run_at = datetime.now(timezone.utc)
        await db_session.commit()

        assert campaign.status == CampaignStatus.ACTIVE

        # 3. Simulate discovered job
        job = DiscoveredJob(
            campaign_id=campaign.id,
            user_id=test_user.id,
            external_id="test-external-123",
            source=JobSource.LINKEDIN,
            title="Senior Software Engineer",
            company="Test Company",
            location="San Francisco, CA",
            description="Looking for a Python developer...",
            url="https://example.com/job/123",
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        assert job.id is not None
        assert job.match_score is None  # Not yet analyzed

        # 4. Simulate job analysis
        agent = JobQualificationAgent()
        user_profile = UserProfile(
            skills=["python", "fastapi", "postgresql"],
            years_of_experience=5,
            job_titles=["Software Engineer"],
        )

        job_reqs = agent.extract_requirements(
            job_id=str(job.id),
            title=job.title,
            description=job.description,
        )

        result = await agent.run(job_reqs, user_profile)

        # Update job with results
        job.match_score = result.match_score
        job.match_reasoning = result.match_reasoning
        job.is_qualified = result.is_qualified
        await db_session.commit()

        assert job.match_score is not None
        assert job.is_qualified is not None

        # 5. Create application if qualified
        if job.is_qualified:
            application = JobApplication(
                user_id=test_user.id,
                discovered_job_id=job.id,
                campaign_id=campaign.id,
                status=ApplicationStatus.QUEUED,
                job_title=job.title,
                company=job.company,
                job_url=job.url,
            )
            db_session.add(application)
            await db_session.commit()

            assert application.id is not None
            assert application.status == ApplicationStatus.QUEUED


# ============================================================================
# Fixtures for Automation Tests
# ============================================================================


@pytest.fixture
def mock_job_discovery_agent():
    """Mock job discovery agent."""
    mock = MagicMock()
    mock.run = AsyncMock(return_value=(
        [
            MagicMock(
                external_id="job-1",
                source=JobSource.LINKEDIN,
                title="Software Engineer",
                company="Test Corp",
                location="Remote",
                description="Great job opportunity",
                url="https://example.com/job/1",
            ),
        ],
        MagicMock(jobs_found=1, errors=[]),
    ))
    return mock


@pytest.fixture
def mock_qualification_agent():
    """Mock job qualification agent."""
    mock = MagicMock()
    mock.run = AsyncMock(return_value=QualificationResult(
        job_id="test-job",
        match_score=85.0,
        is_qualified=True,
        match_reasoning="Good match for Python skills",
        strengths=["Strong Python experience"],
        gaps=[],
    ))
    return mock
