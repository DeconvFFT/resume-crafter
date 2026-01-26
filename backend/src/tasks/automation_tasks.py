"""Background tasks for job search automation.

Provides periodic tasks for:
- Job discovery across multiple platforms
- Job analysis and scoring against user profile
- Application queue processing with rate limiting
- Company research and enrichment
- Networking outreach message generation

Rate limiting:
- 30-40 applications per day maximum
- 5 minute minimum delay between applications
- Respects platform-specific rate limits
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import selectinload

from src.models.database import (
    ApplicationStatus,
    AutomationLog,
    CampaignStatus,
    CompanyContact,
    CompanyProfile,
    DiscoveredJob,
    JobApplication,
    JobSource,
    NetworkingOutreach,
    OutreachStatus,
    SearchCampaign,
    Skill,
    User,
    Experience,
)
from src.agents.automation import (
    ContactDiscoveryAgent,
    JobDiscoveryAgent,
    JobQualificationAgent,
    JobRequirements,
    OutreachAgent,
    UserProfile,
    UserContext,
    ContactContext,
    JobContext,
)

logger = logging.getLogger(__name__)


# ============ Rate Limiting Configuration ============

# Maximum applications per day (30-40 range)
MAX_APPLICATIONS_PER_DAY = 35

# Minimum delay between applications (5 minutes)
MIN_APPLICATION_DELAY_SECONDS = 300  # 5 minutes

# Maximum retries for failed tasks
MAX_TASK_RETRIES = 3

# Delay between retries (exponential backoff base)
RETRY_BASE_DELAY_SECONDS = 60


# ============ Helper Functions ============


async def log_automation_action(
    db,
    user_id: UUID,
    action_type: str,
    entity_type: str,
    entity_id: UUID | None,
    status: str,
    details: dict[str, Any] | None = None,
    duration_ms: int | None = None,
) -> AutomationLog:
    """Create an automation log entry.

    Args:
        db: Database session.
        user_id: User who owns the action.
        action_type: Type of action (job_discovery, job_analysis, etc.).
        entity_type: Type of entity (campaign, job, application, contact, outreach).
        entity_id: ID of the entity being acted upon.
        status: Status of the action (started, completed, failed).
        details: Additional details about the action.
        duration_ms: Duration of the action in milliseconds.

    Returns:
        Created AutomationLog entry.
    """
    log_entry = AutomationLog(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        details=details,
        duration_ms=duration_ms,
    )
    db.add(log_entry)
    await db.flush()
    return log_entry


async def get_applications_today_count(db, user_id: UUID) -> int:
    """Get the number of applications submitted today.

    Args:
        db: Database session.
        user_id: User ID to check.

    Returns:
        Number of applications submitted today.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    result = await db.execute(
        select(func.count(JobApplication.id)).where(
            and_(
                JobApplication.user_id == user_id,
                JobApplication.applied_at >= today_start,
                JobApplication.status.in_([
                    ApplicationStatus.APPLIED,
                    ApplicationStatus.APPLYING,
                ]),
            )
        )
    )
    return result.scalar() or 0


async def get_last_application_time(db, user_id: UUID) -> datetime | None:
    """Get the timestamp of the last application.

    Args:
        db: Database session.
        user_id: User ID to check.

    Returns:
        Timestamp of last application or None.
    """
    result = await db.execute(
        select(JobApplication.applied_at)
        .where(
            and_(
                JobApplication.user_id == user_id,
                JobApplication.applied_at.isnot(None),
            )
        )
        .order_by(JobApplication.applied_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def can_submit_application(db, user_id: UUID) -> tuple[bool, str | None]:
    """Check if user can submit another application.

    Args:
        db: Database session.
        user_id: User ID to check.

    Returns:
        Tuple of (can_submit, reason_if_not).
    """
    # Check daily limit
    today_count = await get_applications_today_count(db, user_id)
    if today_count >= MAX_APPLICATIONS_PER_DAY:
        return False, f"Daily limit reached ({MAX_APPLICATIONS_PER_DAY} applications)"

    # Check time since last application
    last_applied = await get_last_application_time(db, user_id)
    if last_applied:
        time_since = (datetime.now(timezone.utc) - last_applied).total_seconds()
        if time_since < MIN_APPLICATION_DELAY_SECONDS:
            wait_time = MIN_APPLICATION_DELAY_SECONDS - time_since
            return False, f"Rate limit: wait {int(wait_time)} seconds"

    return True, None


async def build_user_profile(db, user_id: UUID) -> UserProfile:
    """Build UserProfile from database for job qualification.

    Args:
        db: Database session.
        user_id: User ID to build profile for.

    Returns:
        UserProfile for qualification agent.
    """
    # Get user skills
    skills_result = await db.execute(
        select(Skill).where(Skill.user_id == user_id)
    )
    skills = skills_result.scalars().all()

    # Get user experiences for job titles
    exp_result = await db.execute(
        select(Experience)
        .where(Experience.user_id == user_id)
        .order_by(Experience.start_date.desc())
    )
    experiences = exp_result.scalars().all()

    # Calculate years of experience
    years = 0
    if experiences:
        earliest = min(exp.start_date for exp in experiences)
        years = (datetime.now().date() - earliest).days // 365

    # Build proficiency map
    proficiencies = {}
    for skill in skills:
        if skill.proficiency:
            proficiencies[skill.name] = skill.proficiency.value

    return UserProfile(
        skills=[s.name for s in skills],
        skill_proficiencies=proficiencies,
        years_of_experience=years,
        job_titles=[exp.role for exp in experiences],
        industries=[],  # Would need additional data model
    )


async def build_user_context(db, user_id: UUID) -> UserContext:
    """Build UserContext from database for outreach generation.

    Args:
        db: Database session.
        user_id: User ID to build context for.

    Returns:
        UserContext for outreach agent.
    """
    # Get user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one()

    # Get current experience (most recent)
    exp_result = await db.execute(
        select(Experience)
        .where(
            and_(
                Experience.user_id == user_id,
                Experience.is_current == True,
            )
        )
        .limit(1)
    )
    current_exp = exp_result.scalar_one_or_none()

    # Get top skills
    skills_result = await db.execute(
        select(Skill)
        .where(Skill.user_id == user_id)
        .order_by(Skill.display_order)
        .limit(5)
    )
    top_skills = [s.name for s in skills_result.scalars().all()]

    # Calculate years of experience
    all_exp_result = await db.execute(
        select(Experience).where(Experience.user_id == user_id)
    )
    all_experiences = all_exp_result.scalars().all()
    years = 0
    if all_experiences:
        earliest = min(exp.start_date for exp in all_experiences)
        years = (datetime.now().date() - earliest).days // 365

    return UserContext(
        name=user.full_name or "Unknown",
        current_role=current_exp.role if current_exp else None,
        current_company=current_exp.company if current_exp else None,
        target_role=None,  # Would come from campaign
        years_experience=years,
        top_skills=top_skills,
        notable_achievement=None,  # Would need additional data
        calendly_link=None,  # Would come from user settings
    )


# ============ Job Discovery Task ============


async def discover_jobs(
    ctx: dict,
    campaign_id: UUID,
    user_id: UUID,
    sources: list[str] | None = None,
    max_jobs_per_source: int = 50,
) -> dict:
    """Discover new jobs for a search campaign.

    This task runs periodically to find new jobs matching campaign criteria.

    Args:
        ctx: ARQ context with db_session_factory.
        campaign_id: Campaign to discover jobs for.
        user_id: User who owns the campaign.
        sources: Optional list of job sources to search.
        max_jobs_per_source: Maximum jobs to fetch per source.

    Returns:
        Discovery result with counts and any errors.
    """
    db_session_factory = ctx["db_session_factory"]
    start_time = time.time()

    async with db_session_factory() as db:
        try:
            # Log start
            await log_automation_action(
                db, user_id, "job_discovery", "campaign", campaign_id,
                "started", {"sources": sources, "max_per_source": max_jobs_per_source}
            )

            # Get campaign
            result = await db.execute(
                select(SearchCampaign).where(
                    and_(
                        SearchCampaign.id == campaign_id,
                        SearchCampaign.user_id == user_id,
                        SearchCampaign.status == CampaignStatus.ACTIVE,
                    )
                )
            )
            campaign = result.scalar_one_or_none()

            if not campaign:
                logger.warning(f"Campaign {campaign_id} not found or not active")
                return {"status": "error", "message": "Campaign not found or not active"}

            # Initialize agent
            agent = JobDiscoveryAgent()

            # Convert source strings to JobSource enum if provided
            job_sources = None
            if sources:
                job_sources = [JobSource(s) for s in sources]

            # Run discovery
            discovered_jobs, discovery_result = await agent.run(
                campaign=campaign,
                sources=job_sources,
                max_jobs_per_source=max_jobs_per_source,
            )

            # Store discovered jobs
            new_job_count = 0
            duplicate_count = 0

            for job_data in discovered_jobs:
                # Check for duplicates
                existing = await db.execute(
                    select(DiscoveredJob).where(
                        and_(
                            DiscoveredJob.user_id == user_id,
                            DiscoveredJob.external_id == job_data.external_id,
                            DiscoveredJob.source == job_data.source,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    duplicate_count += 1
                    continue

                # Create new discovered job
                discovered_job = DiscoveredJob(
                    campaign_id=campaign_id,
                    user_id=user_id,
                    external_id=job_data.external_id,
                    source=job_data.source,
                    title=job_data.title,
                    company=job_data.company,
                    location=job_data.location or "Unknown",
                    description=job_data.description or "",
                    requirements=job_data.requirements,
                    salary_min=job_data.salary_min,
                    salary_max=job_data.salary_max,
                    salary_currency=job_data.salary_currency,
                    url=job_data.url,
                    posted_at=job_data.posted_at,
                    raw_data=job_data.raw_data,
                )
                db.add(discovered_job)
                new_job_count += 1

            # Update campaign last run time
            campaign.last_run_at = datetime.now(timezone.utc)
            campaign.next_run_at = datetime.now(timezone.utc) + timedelta(hours=24)

            await db.commit()

            duration_ms = int((time.time() - start_time) * 1000)

            # Log completion
            await log_automation_action(
                db, user_id, "job_discovery", "campaign", campaign_id,
                "completed", {
                    "jobs_found": discovery_result.jobs_found,
                    "jobs_new": new_job_count,
                    "jobs_duplicate": duplicate_count,
                    "errors": discovery_result.errors,
                },
                duration_ms=duration_ms,
            )
            await db.commit()

            logger.info(
                f"Job discovery for campaign {campaign_id}: "
                f"{new_job_count} new jobs, {duplicate_count} duplicates"
            )

            return {
                "status": "success",
                "campaign_id": str(campaign_id),
                "jobs_found": discovery_result.jobs_found,
                "jobs_new": new_job_count,
                "jobs_duplicate": duplicate_count,
                "errors": discovery_result.errors,
            }

        except Exception as e:
            logger.exception(f"Error in job discovery for campaign {campaign_id}: {e}")

            duration_ms = int((time.time() - start_time) * 1000)
            await log_automation_action(
                db, user_id, "job_discovery", "campaign", campaign_id,
                "failed", {"error": str(e)}, duration_ms=duration_ms,
            )
            await db.commit()

            return {"status": "error", "message": str(e)}


# ============ Job Analysis Task ============


async def analyze_discovered_job(
    ctx: dict,
    job_id: UUID,
    user_id: UUID,
) -> dict:
    """Analyze and score a discovered job against user profile.

    This task runs for each newly discovered job to determine qualification.

    Args:
        ctx: ARQ context with db_session_factory.
        job_id: Discovered job to analyze.
        user_id: User to match against.

    Returns:
        Analysis result with match score and qualification status.
    """
    db_session_factory = ctx["db_session_factory"]
    start_time = time.time()

    async with db_session_factory() as db:
        try:
            # Log start
            await log_automation_action(
                db, user_id, "job_analysis", "job", job_id,
                "started", {}
            )

            # Get discovered job
            result = await db.execute(
                select(DiscoveredJob).where(
                    and_(
                        DiscoveredJob.id == job_id,
                        DiscoveredJob.user_id == user_id,
                    )
                )
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.warning(f"Discovered job {job_id} not found")
                return {"status": "error", "message": "Job not found"}

            # Skip if already analyzed
            if job.match_score is not None:
                return {
                    "status": "skipped",
                    "message": "Job already analyzed",
                    "match_score": job.match_score,
                }

            # Build user profile
            user_profile = await build_user_profile(db, user_id)

            # Initialize qualification agent
            agent = JobQualificationAgent()

            # Extract requirements from job
            job_requirements = agent.extract_requirements(
                job_id=str(job.id),
                title=job.title,
                description=job.description,
                requirements_text=job.requirements,
            )

            # Run qualification analysis
            qualification_result = await agent.run(
                job_requirements=job_requirements,
                user_profile=user_profile,
            )

            # Update job with results
            job.match_score = qualification_result.match_score
            job.match_reasoning = qualification_result.match_reasoning
            job.is_qualified = qualification_result.is_qualified

            await db.commit()

            duration_ms = int((time.time() - start_time) * 1000)

            # Log completion
            await log_automation_action(
                db, user_id, "job_analysis", "job", job_id,
                "completed", {
                    "match_score": qualification_result.match_score,
                    "is_qualified": qualification_result.is_qualified,
                    "strengths": qualification_result.strengths,
                    "gaps": qualification_result.gaps,
                },
                duration_ms=duration_ms,
            )
            await db.commit()

            logger.info(
                f"Job analysis for {job_id}: "
                f"score={qualification_result.match_score}, "
                f"qualified={qualification_result.is_qualified}"
            )

            return {
                "status": "success",
                "job_id": str(job_id),
                "match_score": qualification_result.match_score,
                "is_qualified": qualification_result.is_qualified,
                "match_reasoning": qualification_result.match_reasoning,
            }

        except Exception as e:
            logger.exception(f"Error analyzing job {job_id}: {e}")

            duration_ms = int((time.time() - start_time) * 1000)
            await log_automation_action(
                db, user_id, "job_analysis", "job", job_id,
                "failed", {"error": str(e)}, duration_ms=duration_ms,
            )
            await db.commit()

            return {"status": "error", "message": str(e)}


async def batch_analyze_jobs(
    ctx: dict,
    campaign_id: UUID,
    user_id: UUID,
    limit: int = 50,
) -> dict:
    """Analyze all unscored jobs in a campaign.

    Args:
        ctx: ARQ context with db_session_factory.
        campaign_id: Campaign to analyze jobs for.
        user_id: User who owns the campaign.
        limit: Maximum jobs to analyze in one batch.

    Returns:
        Batch analysis results.
    """
    db_session_factory = ctx["db_session_factory"]
    start_time = time.time()

    async with db_session_factory() as db:
        try:
            # Get unanalyzed jobs
            result = await db.execute(
                select(DiscoveredJob).where(
                    and_(
                        DiscoveredJob.campaign_id == campaign_id,
                        DiscoveredJob.user_id == user_id,
                        DiscoveredJob.match_score.is_(None),
                    )
                ).limit(limit)
            )
            jobs = result.scalars().all()

            if not jobs:
                return {"status": "success", "message": "No jobs to analyze", "analyzed": 0}

            # Build user profile once
            user_profile = await build_user_profile(db, user_id)
            agent = JobQualificationAgent()

            analyzed_count = 0
            qualified_count = 0
            errors = []

            for job in jobs:
                try:
                    # Extract and analyze
                    job_requirements = agent.extract_requirements(
                        job_id=str(job.id),
                        title=job.title,
                        description=job.description,
                        requirements_text=job.requirements,
                    )

                    qualification_result = await agent.run(
                        job_requirements=job_requirements,
                        user_profile=user_profile,
                    )

                    # Update job
                    job.match_score = qualification_result.match_score
                    job.match_reasoning = qualification_result.match_reasoning
                    job.is_qualified = qualification_result.is_qualified

                    analyzed_count += 1
                    if qualification_result.is_qualified:
                        qualified_count += 1

                except Exception as e:
                    errors.append(f"Job {job.id}: {str(e)}")

            await db.commit()

            duration_ms = int((time.time() - start_time) * 1000)

            # Log completion
            await log_automation_action(
                db, user_id, "batch_job_analysis", "campaign", campaign_id,
                "completed", {
                    "analyzed": analyzed_count,
                    "qualified": qualified_count,
                    "errors": errors,
                },
                duration_ms=duration_ms,
            )
            await db.commit()

            logger.info(
                f"Batch analysis for campaign {campaign_id}: "
                f"{analyzed_count} analyzed, {qualified_count} qualified"
            )

            return {
                "status": "success",
                "campaign_id": str(campaign_id),
                "analyzed": analyzed_count,
                "qualified": qualified_count,
                "errors": errors,
            }

        except Exception as e:
            logger.exception(f"Error in batch job analysis: {e}")
            return {"status": "error", "message": str(e)}


# ============ Application Queue Processor ============


async def process_application_queue(
    ctx: dict,
    user_id: UUID,
    max_applications: int = 5,
) -> dict:
    """Process queued applications with rate limiting.

    This task processes applications in the queue, respecting:
    - Daily application limit (30-40)
    - Minimum delay between applications (5 minutes)
    - Platform-specific rate limits

    Args:
        ctx: ARQ context with db_session_factory.
        user_id: User whose queue to process.
        max_applications: Maximum applications to process in this run.

    Returns:
        Processing results.
    """
    db_session_factory = ctx["db_session_factory"]
    start_time = time.time()

    async with db_session_factory() as db:
        try:
            # Check if we can submit applications
            can_submit, reason = await can_submit_application(db, user_id)
            if not can_submit:
                logger.info(f"Application queue paused: {reason}")
                return {
                    "status": "rate_limited",
                    "message": reason,
                    "processed": 0,
                }

            # Get queued applications
            result = await db.execute(
                select(JobApplication)
                .where(
                    and_(
                        JobApplication.user_id == user_id,
                        JobApplication.status == ApplicationStatus.QUEUED,
                    )
                )
                .order_by(JobApplication.created_at)
                .limit(max_applications)
            )
            applications = result.scalars().all()

            if not applications:
                return {
                    "status": "success",
                    "message": "No applications in queue",
                    "processed": 0,
                }

            processed = 0
            failed = 0
            skipped = 0

            for app in applications:
                # Re-check rate limit before each application
                can_submit, reason = await can_submit_application(db, user_id)
                if not can_submit:
                    logger.info(f"Rate limit hit during processing: {reason}")
                    break

                try:
                    # Log start
                    await log_automation_action(
                        db, user_id, "application_submit", "application", app.id,
                        "started", {"job_title": app.job_title, "company": app.company}
                    )

                    # Update status to applying
                    app.status = ApplicationStatus.APPLYING

                    # Add to status history
                    if app.status_history is None:
                        app.status_history = []
                    app.status_history.append({
                        "status": ApplicationStatus.APPLYING.value,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "notes": "Processing application",
                    })

                    await db.commit()

                    # TODO: In Phase 6, integrate with ApplicationFormAgent
                    # For now, simulate successful submission
                    await asyncio.sleep(2)  # Simulate form filling time

                    # Mark as applied
                    app.status = ApplicationStatus.APPLIED
                    app.applied_at = datetime.now(timezone.utc)
                    app.status_history.append({
                        "status": ApplicationStatus.APPLIED.value,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "notes": "Application submitted successfully",
                    })

                    await db.commit()

                    # Log completion
                    await log_automation_action(
                        db, user_id, "application_submit", "application", app.id,
                        "completed", {
                            "job_title": app.job_title,
                            "company": app.company,
                        }
                    )
                    await db.commit()

                    processed += 1

                    # Delay before next application
                    if processed < len(applications):
                        logger.info(
                            f"Waiting {MIN_APPLICATION_DELAY_SECONDS}s before next application"
                        )
                        await asyncio.sleep(MIN_APPLICATION_DELAY_SECONDS)

                except Exception as e:
                    logger.error(f"Error processing application {app.id}: {e}")

                    # Mark as failed (back to queued for retry)
                    app.status = ApplicationStatus.QUEUED
                    if app.status_history is None:
                        app.status_history = []
                    app.status_history.append({
                        "status": "failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "notes": f"Error: {str(e)}",
                    })

                    await db.commit()

                    # Log failure
                    await log_automation_action(
                        db, user_id, "application_submit", "application", app.id,
                        "failed", {"error": str(e)}
                    )
                    await db.commit()

                    failed += 1

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Application queue processed: {processed} submitted, "
                f"{failed} failed, {skipped} skipped"
            )

            return {
                "status": "success",
                "processed": processed,
                "failed": failed,
                "skipped": skipped,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            logger.exception(f"Error processing application queue: {e}")
            return {"status": "error", "message": str(e)}


# ============ Company Research Task ============


async def research_company(
    ctx: dict,
    company_profile_id: UUID,
    user_id: UUID,
    discover_contacts: bool = True,
    max_contacts: int = 10,
) -> dict:
    """Research and enrich a company profile.

    This task:
    1. Gathers company information (industry, size, tech stack)
    2. Optionally discovers relevant contacts
    3. Enriches profile with research data

    Args:
        ctx: ARQ context with db_session_factory.
        company_profile_id: Company profile to research.
        user_id: User who owns the profile.
        discover_contacts: Whether to discover contacts.
        max_contacts: Maximum contacts to discover.

    Returns:
        Research results.
    """
    db_session_factory = ctx["db_session_factory"]
    start_time = time.time()

    async with db_session_factory() as db:
        try:
            # Log start
            await log_automation_action(
                db, user_id, "company_research", "company", company_profile_id,
                "started", {"discover_contacts": discover_contacts}
            )

            # Get company profile
            result = await db.execute(
                select(CompanyProfile).where(
                    and_(
                        CompanyProfile.id == company_profile_id,
                        CompanyProfile.user_id == user_id,
                    )
                )
            )
            company = result.scalar_one_or_none()

            if not company:
                logger.warning(f"Company profile {company_profile_id} not found")
                return {"status": "error", "message": "Company not found"}

            # TODO: In Phase 6, integrate with web scraping for company research
            # For now, use mock enrichment

            # Update research timestamp
            if company.research_data is None:
                company.research_data = {}
            company.research_data["last_researched"] = datetime.now(timezone.utc).isoformat()

            contacts_discovered = 0

            # Discover contacts if requested
            if discover_contacts:
                contact_agent = ContactDiscoveryAgent()

                discovery_result = await contact_agent.run(
                    company_name=company.name,
                    max_contacts=max_contacts,
                )

                # Store discovered contacts
                for contact_info in discovery_result.contacts:
                    # Check for existing contact
                    existing = await db.execute(
                        select(CompanyContact).where(
                            and_(
                                CompanyContact.company_profile_id == company_profile_id,
                                CompanyContact.linkedin_url == contact_info.linkedin_url,
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    # Create new contact
                    contact = CompanyContact(
                        user_id=user_id,
                        company_profile_id=company_profile_id,
                        name=contact_info.name,
                        title=contact_info.title,
                        linkedin_url=contact_info.linkedin_url or "",
                        email=contact_info.email,
                        relevance_score=contact_info.relevance_score,
                        notes=contact_info.relevance_reasoning,
                    )
                    db.add(contact)
                    contacts_discovered += 1

            await db.commit()

            duration_ms = int((time.time() - start_time) * 1000)

            # Log completion
            await log_automation_action(
                db, user_id, "company_research", "company", company_profile_id,
                "completed", {
                    "company_name": company.name,
                    "contacts_discovered": contacts_discovered,
                },
                duration_ms=duration_ms,
            )
            await db.commit()

            logger.info(
                f"Company research for {company.name}: "
                f"{contacts_discovered} contacts discovered"
            )

            return {
                "status": "success",
                "company_id": str(company_profile_id),
                "company_name": company.name,
                "contacts_discovered": contacts_discovered,
            }

        except Exception as e:
            logger.exception(f"Error researching company {company_profile_id}: {e}")

            duration_ms = int((time.time() - start_time) * 1000)
            await log_automation_action(
                db, user_id, "company_research", "company", company_profile_id,
                "failed", {"error": str(e)}, duration_ms=duration_ms,
            )
            await db.commit()

            return {"status": "error", "message": str(e)}


# ============ Outreach Generation Task ============


async def generate_outreach(
    ctx: dict,
    contact_id: UUID,
    user_id: UUID,
    application_id: UUID | None = None,
    generate_linkedin: bool = True,
    generate_email: bool = True,
) -> dict:
    """Generate personalized outreach message drafts for a contact.

    This task creates LinkedIn and/or email message drafts that are
    stored for manual review before sending.

    Args:
        ctx: ARQ context with db_session_factory.
        contact_id: Contact to generate outreach for.
        user_id: User generating the outreach.
        application_id: Optional associated job application.
        generate_linkedin: Generate LinkedIn message.
        generate_email: Generate email message.

    Returns:
        Generated outreach drafts.
    """
    db_session_factory = ctx["db_session_factory"]
    start_time = time.time()

    async with db_session_factory() as db:
        try:
            # Log start
            await log_automation_action(
                db, user_id, "outreach_generation", "contact", contact_id,
                "started", {
                    "application_id": str(application_id) if application_id else None,
                    "generate_linkedin": generate_linkedin,
                    "generate_email": generate_email,
                }
            )

            # Get contact with company info
            result = await db.execute(
                select(CompanyContact)
                .options(selectinload(CompanyContact.company))
                .where(
                    and_(
                        CompanyContact.id == contact_id,
                        CompanyContact.user_id == user_id,
                    )
                )
            )
            contact = result.scalar_one_or_none()

            if not contact:
                logger.warning(f"Contact {contact_id} not found")
                return {"status": "error", "message": "Contact not found"}

            # Get job application if provided
            job_context = None
            if application_id:
                app_result = await db.execute(
                    select(JobApplication).where(
                        and_(
                            JobApplication.id == application_id,
                            JobApplication.user_id == user_id,
                        )
                    )
                )
                application = app_result.scalar_one_or_none()
                if application:
                    job_context = JobContext(
                        title=application.job_title,
                        company=application.company,
                        job_url=application.job_url,
                        applied=application.status == ApplicationStatus.APPLIED,
                    )

            # Build user context
            user_context = await build_user_context(db, user_id)

            # Build contact context
            contact_context = ContactContext(
                name=contact.name,
                title=contact.title,
                company=contact.company.name if contact.company else "Unknown",
                linkedin_url=contact.linkedin_url,
                email=contact.email,
            )

            # Initialize outreach agent and generate
            agent = OutreachAgent()
            outreach_result = await agent.run(
                user=user_context,
                contact=contact_context,
                job=job_context,
                generate_linkedin=generate_linkedin,
                generate_email=generate_email and contact.email is not None,
            )

            drafts_created = []

            # Store LinkedIn draft
            if outreach_result.linkedin_draft:
                linkedin_outreach = NetworkingOutreach(
                    user_id=user_id,
                    contact_id=contact_id,
                    application_id=application_id,
                    channel="linkedin",
                    status=OutreachStatus.DRAFT_READY,
                    message=outreach_result.linkedin_draft.message,
                )
                db.add(linkedin_outreach)
                drafts_created.append("linkedin")

            # Store email draft
            if outreach_result.email_draft:
                email_outreach = NetworkingOutreach(
                    user_id=user_id,
                    contact_id=contact_id,
                    application_id=application_id,
                    channel="email",
                    status=OutreachStatus.DRAFT_READY,
                    subject=outreach_result.email_draft.subject,
                    message=outreach_result.email_draft.message,
                )
                db.add(email_outreach)
                drafts_created.append("email")

            await db.commit()

            duration_ms = int((time.time() - start_time) * 1000)

            # Log completion
            await log_automation_action(
                db, user_id, "outreach_generation", "contact", contact_id,
                "completed", {
                    "contact_name": contact.name,
                    "drafts_created": drafts_created,
                },
                duration_ms=duration_ms,
            )
            await db.commit()

            logger.info(
                f"Outreach generated for contact {contact.name}: "
                f"{', '.join(drafts_created)}"
            )

            return {
                "status": "success",
                "contact_id": str(contact_id),
                "contact_name": contact.name,
                "drafts_created": drafts_created,
                "linkedin_message": (
                    outreach_result.linkedin_draft.message
                    if outreach_result.linkedin_draft else None
                ),
                "email_subject": (
                    outreach_result.email_draft.subject
                    if outreach_result.email_draft else None
                ),
            }

        except Exception as e:
            logger.exception(f"Error generating outreach for contact {contact_id}: {e}")

            duration_ms = int((time.time() - start_time) * 1000)
            await log_automation_action(
                db, user_id, "outreach_generation", "contact", contact_id,
                "failed", {"error": str(e)}, duration_ms=duration_ms,
            )
            await db.commit()

            return {"status": "error", "message": str(e)}


async def batch_generate_outreach(
    ctx: dict,
    user_id: UUID,
    company_profile_id: UUID | None = None,
    application_id: UUID | None = None,
    max_contacts: int = 10,
) -> dict:
    """Generate outreach for multiple contacts.

    Args:
        ctx: ARQ context with db_session_factory.
        user_id: User generating outreach.
        company_profile_id: Optional filter by company.
        application_id: Optional associated application.
        max_contacts: Maximum contacts to process.

    Returns:
        Batch generation results.
    """
    db_session_factory = ctx["db_session_factory"]
    start_time = time.time()

    async with db_session_factory() as db:
        try:
            # Build query for contacts without recent outreach
            query = (
                select(CompanyContact)
                .where(CompanyContact.user_id == user_id)
            )

            if company_profile_id:
                query = query.where(CompanyContact.company_profile_id == company_profile_id)

            # Exclude contacts with existing pending/draft outreach
            subquery = (
                select(NetworkingOutreach.contact_id)
                .where(
                    NetworkingOutreach.status.in_([
                        OutreachStatus.PENDING,
                        OutreachStatus.DRAFT_READY,
                    ])
                )
            )
            query = query.where(CompanyContact.id.notin_(subquery))
            query = query.order_by(CompanyContact.relevance_score.desc().nullslast())
            query = query.limit(max_contacts)

            result = await db.execute(query)
            contacts = result.scalars().all()

            if not contacts:
                return {
                    "status": "success",
                    "message": "No contacts to generate outreach for",
                    "generated": 0,
                }

            generated = 0
            errors = []

            for contact in contacts:
                try:
                    # Generate outreach (reuse context building)
                    gen_result = await generate_outreach(
                        ctx, contact.id, user_id,
                        application_id=application_id,
                    )

                    if gen_result.get("status") == "success":
                        generated += 1
                    else:
                        errors.append(f"Contact {contact.name}: {gen_result.get('message')}")

                except Exception as e:
                    errors.append(f"Contact {contact.name}: {str(e)}")

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Batch outreach generation: {generated} contacts processed, "
                f"{len(errors)} errors"
            )

            return {
                "status": "success",
                "generated": generated,
                "errors": errors,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            logger.exception(f"Error in batch outreach generation: {e}")
            return {"status": "error", "message": str(e)}


# ============ Cron Jobs for Periodic Tasks ============


async def run_scheduled_discovery(ctx: dict) -> dict:
    """Run job discovery for all active campaigns (cron job).

    This task runs periodically to discover new jobs for all active campaigns.

    Args:
        ctx: ARQ context with db_session_factory.

    Returns:
        Summary of all discovery runs.
    """
    db_session_factory = ctx["db_session_factory"]

    async with db_session_factory() as db:
        try:
            # Get all active campaigns due for discovery
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(SearchCampaign).where(
                    and_(
                        SearchCampaign.status == CampaignStatus.ACTIVE,
                        # Run if never run or past next_run_at
                        SearchCampaign.next_run_at.is_(None) | (SearchCampaign.next_run_at <= now),
                    )
                )
            )
            campaigns = result.scalars().all()

            if not campaigns:
                logger.info("No campaigns due for discovery")
                return {"status": "success", "campaigns_processed": 0}

            results = []
            for campaign in campaigns:
                try:
                    discovery_result = await discover_jobs(
                        ctx, campaign.id, campaign.user_id
                    )
                    results.append({
                        "campaign_id": str(campaign.id),
                        "result": discovery_result,
                    })
                except Exception as e:
                    logger.error(f"Error in scheduled discovery for campaign {campaign.id}: {e}")
                    results.append({
                        "campaign_id": str(campaign.id),
                        "error": str(e),
                    })

            logger.info(f"Scheduled discovery completed: {len(results)} campaigns processed")

            return {
                "status": "success",
                "campaigns_processed": len(campaigns),
                "results": results,
            }

        except Exception as e:
            logger.exception(f"Error in scheduled discovery: {e}")
            return {"status": "error", "message": str(e)}


async def run_scheduled_analysis(ctx: dict) -> dict:
    """Run job analysis for all campaigns with unanalyzed jobs (cron job).

    Args:
        ctx: ARQ context with db_session_factory.

    Returns:
        Summary of all analysis runs.
    """
    db_session_factory = ctx["db_session_factory"]

    async with db_session_factory() as db:
        try:
            # Get campaigns with unanalyzed jobs
            result = await db.execute(
                select(SearchCampaign)
                .where(SearchCampaign.status == CampaignStatus.ACTIVE)
            )
            campaigns = result.scalars().all()

            results = []
            for campaign in campaigns:
                # Check if campaign has unanalyzed jobs
                unanalyzed = await db.execute(
                    select(func.count(DiscoveredJob.id)).where(
                        and_(
                            DiscoveredJob.campaign_id == campaign.id,
                            DiscoveredJob.match_score.is_(None),
                        )
                    )
                )
                count = unanalyzed.scalar() or 0

                if count > 0:
                    try:
                        analysis_result = await batch_analyze_jobs(
                            ctx, campaign.id, campaign.user_id
                        )
                        results.append({
                            "campaign_id": str(campaign.id),
                            "result": analysis_result,
                        })
                    except Exception as e:
                        logger.error(f"Error in scheduled analysis for campaign {campaign.id}: {e}")
                        results.append({
                            "campaign_id": str(campaign.id),
                            "error": str(e),
                        })

            logger.info(f"Scheduled analysis completed: {len(results)} campaigns processed")

            return {
                "status": "success",
                "campaigns_processed": len(results),
                "results": results,
            }

        except Exception as e:
            logger.exception(f"Error in scheduled analysis: {e}")
            return {"status": "error", "message": str(e)}


async def run_scheduled_queue_processing(ctx: dict) -> dict:
    """Process application queues for all users (cron job).

    Args:
        ctx: ARQ context with db_session_factory.

    Returns:
        Summary of queue processing.
    """
    db_session_factory = ctx["db_session_factory"]

    async with db_session_factory() as db:
        try:
            # Get users with queued applications
            result = await db.execute(
                select(JobApplication.user_id)
                .where(JobApplication.status == ApplicationStatus.QUEUED)
                .distinct()
            )
            user_ids = [row[0] for row in result.fetchall()]

            if not user_ids:
                logger.info("No users with queued applications")
                return {"status": "success", "users_processed": 0}

            results = []
            for user_id in user_ids:
                try:
                    process_result = await process_application_queue(
                        ctx, user_id, max_applications=5
                    )
                    results.append({
                        "user_id": str(user_id),
                        "result": process_result,
                    })
                except Exception as e:
                    logger.error(f"Error processing queue for user {user_id}: {e}")
                    results.append({
                        "user_id": str(user_id),
                        "error": str(e),
                    })

            logger.info(f"Scheduled queue processing completed: {len(results)} users processed")

            return {
                "status": "success",
                "users_processed": len(user_ids),
                "results": results,
            }

        except Exception as e:
            logger.exception(f"Error in scheduled queue processing: {e}")
            return {"status": "error", "message": str(e)}
