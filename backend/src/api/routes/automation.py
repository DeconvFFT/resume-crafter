"""Automation API routes for job search, applications, and networking."""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import CurrentUser
from src.models.database import (
    ApplicationStatus,
    AutomationLog,
    CampaignStatus,
    CompanyContact,
    CompanyProfile,
    DiscoveredJob,
    JobApplication,
    NetworkingOutreach,
    OutreachStatus,
    SearchCampaign,
)
from src.models.schemas.automation import (
    ApplicationPipelineStats,
    AutomationDashboard,
    AutomationLogListResponse,
    AutomationLogResponse,
    CompanyContactListResponse,
    CompanyContactResponse,
    CompanyProfileListResponse,
    CompanyProfileResponse,
    DiscoveredJobListResponse,
    DiscoveredJobResponse,
    JobApplicationCreate,
    JobApplicationListResponse,
    JobApplicationResponse,
    JobApplicationUpdate,
    NetworkingOutreachListResponse,
    NetworkingOutreachResponse,
    NetworkingOutreachUpdate,
    SearchCampaignCreate,
    SearchCampaignListResponse,
    SearchCampaignResponse,
)
from src.storage.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


# ============ Request/Response Schemas for specific endpoints ============


class BulkActionRequest(BaseModel):
    """Request schema for bulk actions on discovered jobs."""

    job_ids: list[str] = Field(..., min_length=1, description="List of job IDs to act on")
    action: str = Field(..., pattern="^(approve|reject)$", description="Action to perform")


class BulkActionResponse(BaseModel):
    """Response schema for bulk actions."""

    processed: int
    failed: int
    errors: list[dict[str, Any]] | None = None


class QueueApplicationRequest(BaseModel):
    """Request schema for queuing a job application."""

    discovered_job_id: str = Field(..., description="ID of the discovered job to queue")
    notes: str | None = Field(None, description="Optional notes for the application")


class ApplicationStatusUpdate(BaseModel):
    """Request schema for manual status update."""

    status: str = Field(
        ...,
        pattern="^(discovered|filtered|queued|resume_generated|applying|applied|viewed|response_received|interview_scheduled|rejected|offer_received)$",
    )
    notes: str | None = None


class FindContactsRequest(BaseModel):
    """Request schema for finding contacts at a company."""

    roles: list[str] | None = Field(
        None, description="Target roles to find (e.g., 'Engineering Manager', 'Recruiter')"
    )
    limit: int = Field(10, ge=1, le=50, description="Maximum contacts to discover")


class FindContactsResponse(BaseModel):
    """Response schema for contact discovery."""

    contacts_found: int
    contacts: list[CompanyContactResponse]


class AnalyzeJobResponse(BaseModel):
    """Response schema for job analysis."""

    job_id: str
    match_score: float | None
    match_reasoning: str | None
    is_qualified: bool | None


# ============ Campaign Endpoints ============


@router.post("/campaigns", response_model=SearchCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: SearchCampaignCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchCampaign:
    """Create a new search campaign."""
    campaign = SearchCampaign(
        user_id=current_user.id,
        name=request.name,
        status=CampaignStatus.DRAFT,
        target_roles=request.target_roles,
        target_locations=request.target_locations,
        target_companies=request.target_companies,
        keywords=request.keywords,
        excluded_keywords=request.excluded_keywords,
        min_salary=request.min_salary,
        max_salary=request.max_salary,
        remote_preference=request.remote_preference,
        experience_level=request.experience_level,
        settings=request.settings,
    )
    db.add(campaign)
    await db.flush()

    # Log the action
    log_entry = AutomationLog(
        user_id=current_user.id,
        action_type="campaign_create",
        entity_type="campaign",
        entity_id=campaign.id,
        status="completed",
        details={"campaign_name": request.name},
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(campaign)

    logger.info(f"Created campaign {campaign.id} for user {current_user.id}")
    return campaign


async def _ensure_sample_campaigns_for_user(
    user_id: UUID,
    db: AsyncSession,
) -> None:
    """Create sample campaigns for a user if none exist (for development/demo).

    This helps users see how the automation features work without having to
    create campaigns manually.
    """
    # Check if user already has any campaigns
    count_result = await db.execute(
        select(func.count()).where(
            SearchCampaign.user_id == user_id,
            SearchCampaign.deleted_at.is_(None),
        )
    )
    existing_count = count_result.scalar() or 0

    if existing_count > 0:
        return  # User already has campaigns

    # Create sample campaigns
    sample_campaigns = [
        SearchCampaign(
            user_id=user_id,
            name="Senior Software Engineer - Remote",
            status=CampaignStatus.ACTIVE,
            target_roles=["Senior Software Engineer", "Staff Engineer", "Tech Lead"],
            target_locations=["Remote", "San Francisco, CA", "New York, NY"],
            target_companies=["Google", "Meta", "Amazon", "Microsoft", "Apple"],
            keywords=["Python", "distributed systems", "backend"],
            excluded_keywords=["junior", "intern", "entry-level"],
            min_salary=180000,
            max_salary=350000,
            remote_preference="remote",
            experience_level="senior",
            settings={"auto_apply": False, "daily_limit": 10},
        ),
        SearchCampaign(
            user_id=user_id,
            name="ML Engineer Opportunities",
            status=CampaignStatus.DRAFT,
            target_roles=["Machine Learning Engineer", "ML Engineer", "AI Engineer"],
            target_locations=["Remote", "Seattle, WA", "Boston, MA"],
            target_companies=None,
            keywords=["machine learning", "PyTorch", "TensorFlow", "LLM"],
            excluded_keywords=None,
            min_salary=200000,
            max_salary=400000,
            remote_preference="hybrid",
            experience_level="senior",
            settings={"auto_apply": False, "daily_limit": 5},
        ),
        SearchCampaign(
            user_id=user_id,
            name="Startup Tech Roles",
            status=CampaignStatus.PAUSED,
            target_roles=["Founding Engineer", "Principal Engineer", "CTO"],
            target_locations=["San Francisco, CA", "New York, NY", "Austin, TX"],
            target_companies=None,
            keywords=["startup", "equity", "early-stage", "Series A", "Series B"],
            excluded_keywords=["enterprise", "government", "contractor"],
            min_salary=150000,
            max_salary=None,
            remote_preference="any",
            experience_level="lead",
            settings={"auto_apply": False, "daily_limit": 3},
        ),
    ]

    for campaign in sample_campaigns:
        db.add(campaign)

    await db.flush()
    await db.commit()
    logger.info(f"Created {len(sample_campaigns)} sample campaigns for user {user_id}")


@router.get("/campaigns", response_model=SearchCampaignListResponse)
async def list_campaigns(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status", pattern="^(draft|active|paused|completed)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> SearchCampaignListResponse:
    """List all search campaigns for the current user."""
    # Ensure sample campaigns exist for development/demo (creates if none exist)
    await _ensure_sample_campaigns_for_user(current_user.id, db)

    query = select(SearchCampaign).where(
        SearchCampaign.user_id == current_user.id,
        SearchCampaign.deleted_at.is_(None),
    )

    if status_filter:
        query = query.where(SearchCampaign.status == CampaignStatus(status_filter))

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get items with pagination
    query = query.order_by(SearchCampaign.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    campaigns = result.scalars().all()

    return SearchCampaignListResponse(items=list(campaigns), total=total)


@router.get("/campaigns/{campaign_id}", response_model=SearchCampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchCampaign:
    """Get details of a specific campaign."""
    result = await db.execute(
        select(SearchCampaign).where(
            SearchCampaign.id == campaign_id,
            SearchCampaign.user_id == current_user.id,
            SearchCampaign.deleted_at.is_(None),
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    return campaign


@router.post("/campaigns/{campaign_id}/activate", response_model=SearchCampaignResponse)
async def activate_campaign(
    campaign_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchCampaign:
    """Activate a campaign to start job discovery."""
    result = await db.execute(
        select(SearchCampaign).where(
            SearchCampaign.id == campaign_id,
            SearchCampaign.user_id == current_user.id,
            SearchCampaign.deleted_at.is_(None),
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.status == CampaignStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign is already active"
        )

    campaign.status = CampaignStatus.ACTIVE
    campaign.next_run_at = datetime.now(timezone.utc)

    # Log the action
    log_entry = AutomationLog(
        user_id=current_user.id,
        action_type="campaign_activate",
        entity_type="campaign",
        entity_id=campaign.id,
        status="completed",
        details={"previous_status": campaign.status.value if hasattr(campaign.status, 'value') else str(campaign.status)},
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(campaign)

    logger.info(f"Activated campaign {campaign_id} for user {current_user.id}")
    return campaign


@router.post("/campaigns/{campaign_id}/pause", response_model=SearchCampaignResponse)
async def pause_campaign(
    campaign_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SearchCampaign:
    """Pause an active campaign."""
    result = await db.execute(
        select(SearchCampaign).where(
            SearchCampaign.id == campaign_id,
            SearchCampaign.user_id == current_user.id,
            SearchCampaign.deleted_at.is_(None),
        )
    )
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    if campaign.status != CampaignStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign is not active"
        )

    campaign.status = CampaignStatus.PAUSED
    campaign.next_run_at = None

    # Log the action
    log_entry = AutomationLog(
        user_id=current_user.id,
        action_type="campaign_pause",
        entity_type="campaign",
        entity_id=campaign.id,
        status="completed",
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(campaign)

    logger.info(f"Paused campaign {campaign_id} for user {current_user.id}")
    return campaign


# ============ Job Discovery Endpoints ============


@router.get("/discovered-jobs", response_model=DiscoveredJobListResponse)
async def list_discovered_jobs(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    campaign_id: UUID | None = Query(None, description="Filter by campaign ID"),
    min_score: float | None = Query(None, ge=0, le=100, description="Minimum match score"),
    is_qualified: bool | None = Query(None, description="Filter by qualification status"),
    company: str | None = Query(None, description="Filter by company name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> DiscoveredJobListResponse:
    """List discovered jobs with filters."""
    query = select(DiscoveredJob).where(
        DiscoveredJob.user_id == current_user.id,
        DiscoveredJob.deleted_at.is_(None),
    )

    if campaign_id:
        query = query.where(DiscoveredJob.campaign_id == campaign_id)
    if min_score is not None:
        query = query.where(DiscoveredJob.match_score >= min_score)
    if is_qualified is not None:
        query = query.where(DiscoveredJob.is_qualified == is_qualified)
    if company:
        query = query.where(DiscoveredJob.company.ilike(f"%{company}%"))

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get items with pagination
    query = query.order_by(DiscoveredJob.match_score.desc().nullslast(), DiscoveredJob.created_at.desc())
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return DiscoveredJobListResponse(items=list(jobs), total=total)


@router.post("/discovered-jobs/{job_id}/analyze", response_model=AnalyzeJobResponse)
async def analyze_discovered_job(
    job_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalyzeJobResponse:
    """Analyze and score a discovered job against user profile."""
    result = await db.execute(
        select(DiscoveredJob).where(
            DiscoveredJob.id == job_id,
            DiscoveredJob.user_id == current_user.id,
            DiscoveredJob.deleted_at.is_(None),
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Log the start of analysis
    log_entry = AutomationLog(
        user_id=current_user.id,
        action_type="job_analysis",
        entity_type="discovered_job",
        entity_id=job.id,
        status="started",
    )
    db.add(log_entry)
    await db.flush()

    # TODO: Integrate with actual job analysis agent
    # For now, we'll set placeholder values
    # In production, this would call the analysis agent/service
    job.match_score = 75.0  # Placeholder
    job.match_reasoning = "Analysis pending - integrate with job matching service"
    job.is_qualified = True

    # Update log entry
    log_entry.status = "completed"
    log_entry.details = {"match_score": job.match_score}

    await db.commit()
    await db.refresh(job)

    logger.info(f"Analyzed job {job_id} for user {current_user.id}")
    return AnalyzeJobResponse(
        job_id=str(job.id),
        match_score=job.match_score,
        match_reasoning=job.match_reasoning,
        is_qualified=job.is_qualified,
    )


@router.post("/discovered-jobs/bulk-action", response_model=BulkActionResponse)
async def bulk_action_discovered_jobs(
    request: BulkActionRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkActionResponse:
    """Perform bulk approve/reject actions on discovered jobs."""
    processed = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    for job_id_str in request.job_ids:
        try:
            job_id = UUID(job_id_str)
            result = await db.execute(
                select(DiscoveredJob).where(
                    DiscoveredJob.id == job_id,
                    DiscoveredJob.user_id == current_user.id,
                    DiscoveredJob.deleted_at.is_(None),
                )
            )
            job = result.scalar_one_or_none()

            if not job:
                failed += 1
                errors.append({"job_id": job_id_str, "error": "Job not found"})
                continue

            if request.action == "approve":
                job.is_qualified = True
            elif request.action == "reject":
                job.is_qualified = False

            processed += 1
        except ValueError:
            failed += 1
            errors.append({"job_id": job_id_str, "error": "Invalid UUID format"})
        except Exception as e:
            failed += 1
            errors.append({"job_id": job_id_str, "error": str(e)})

    # Log the bulk action
    log_entry = AutomationLog(
        user_id=current_user.id,
        action_type=f"bulk_{request.action}",
        entity_type="discovered_job",
        status="completed",
        details={"processed": processed, "failed": failed, "total": len(request.job_ids)},
    )
    db.add(log_entry)
    await db.commit()

    logger.info(f"Bulk {request.action} on {processed} jobs for user {current_user.id}")
    return BulkActionResponse(
        processed=processed,
        failed=failed,
        errors=errors if errors else None,
    )


# ============ Application Endpoints ============


@router.get("/applications", response_model=JobApplicationListResponse)
async def list_applications(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern="^(discovered|filtered|queued|resume_generated|applying|applied|viewed|response_received|interview_scheduled|rejected|offer_received)$",
    ),
    campaign_id: UUID | None = Query(None, description="Filter by campaign ID"),
    company: str | None = Query(None, description="Filter by company name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> JobApplicationListResponse:
    """List all job applications with filters."""
    query = select(JobApplication).where(
        JobApplication.user_id == current_user.id,
        JobApplication.deleted_at.is_(None),
    )

    if status_filter:
        query = query.where(JobApplication.status == ApplicationStatus(status_filter))
    if campaign_id:
        query = query.where(JobApplication.campaign_id == campaign_id)
    if company:
        query = query.where(JobApplication.company.ilike(f"%{company}%"))

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get items with pagination
    query = query.order_by(JobApplication.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    applications = result.scalars().all()

    return JobApplicationListResponse(items=list(applications), total=total)


@router.post("/applications/queue", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
async def queue_application(
    request: QueueApplicationRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobApplication:
    """Queue a discovered job for application."""
    # Get the discovered job
    discovered_job_id = UUID(request.discovered_job_id)
    result = await db.execute(
        select(DiscoveredJob).where(
            DiscoveredJob.id == discovered_job_id,
            DiscoveredJob.user_id == current_user.id,
            DiscoveredJob.deleted_at.is_(None),
        )
    )
    discovered_job = result.scalar_one_or_none()

    if not discovered_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovered job not found")

    # Check if application already exists
    existing_result = await db.execute(
        select(JobApplication).where(
            JobApplication.discovered_job_id == discovered_job_id,
            JobApplication.user_id == current_user.id,
            JobApplication.deleted_at.is_(None),
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application already exists for this job",
        )

    # Create application
    application = JobApplication(
        user_id=current_user.id,
        discovered_job_id=discovered_job.id,
        campaign_id=discovered_job.campaign_id,
        status=ApplicationStatus.QUEUED,
        job_title=discovered_job.title,
        company=discovered_job.company,
        job_url=discovered_job.url,
        notes=request.notes,
        status_history=[
            {
                "status": "queued",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notes": "Application queued",
            }
        ],
    )
    db.add(application)
    await db.flush()

    # Log the action
    log_entry = AutomationLog(
        user_id=current_user.id,
        action_type="application_queue",
        entity_type="application",
        entity_id=application.id,
        status="completed",
        details={"job_title": discovered_job.title, "company": discovered_job.company},
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(application)

    logger.info(f"Queued application {application.id} for user {current_user.id}")
    return application


@router.patch("/applications/{application_id}/status", response_model=JobApplicationResponse)
async def update_application_status(
    application_id: UUID,
    request: ApplicationStatusUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobApplication:
    """Manually update application status."""
    result = await db.execute(
        select(JobApplication).where(
            JobApplication.id == application_id,
            JobApplication.user_id == current_user.id,
            JobApplication.deleted_at.is_(None),
        )
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    old_status = application.status.value if hasattr(application.status, 'value') else str(application.status)
    new_status = ApplicationStatus(request.status)

    # Update status
    application.status = new_status

    # Update timestamp fields based on status
    now = datetime.now(timezone.utc)
    if new_status == ApplicationStatus.APPLIED:
        application.applied_at = now
    elif new_status == ApplicationStatus.RESPONSE_RECEIVED:
        application.response_received_at = now
    elif new_status == ApplicationStatus.INTERVIEW_SCHEDULED:
        application.interview_scheduled_at = now

    # Append to status history
    history_entry = {
        "status": request.status,
        "timestamp": now.isoformat(),
        "notes": request.notes,
    }
    if application.status_history:
        application.status_history = application.status_history + [history_entry]
    else:
        application.status_history = [history_entry]

    # Log the action
    log_entry = AutomationLog(
        user_id=current_user.id,
        action_type="application_status_update",
        entity_type="application",
        entity_id=application.id,
        status="completed",
        details={"old_status": old_status, "new_status": request.status},
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(application)

    logger.info(f"Updated application {application_id} status to {request.status} for user {current_user.id}")
    return application


# ============ Networking Endpoints ============


@router.get("/companies", response_model=CompanyProfileListResponse)
async def list_companies(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    industry: str | None = Query(None, description="Filter by industry"),
    search: str | None = Query(None, description="Search by company name"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> CompanyProfileListResponse:
    """List company profiles for the current user."""
    query = select(CompanyProfile).where(
        CompanyProfile.user_id == current_user.id,
        CompanyProfile.deleted_at.is_(None),
    )

    if industry:
        query = query.where(CompanyProfile.industry.ilike(f"%{industry}%"))
    if search:
        query = query.where(CompanyProfile.name.ilike(f"%{search}%"))

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get items with pagination
    query = query.order_by(CompanyProfile.name).offset(offset).limit(limit)
    result = await db.execute(query)
    companies = result.scalars().all()

    return CompanyProfileListResponse(items=list(companies), total=total)


@router.post("/companies/{company_id}/find-contacts", response_model=FindContactsResponse)
async def find_company_contacts(
    company_id: UUID,
    request: FindContactsRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindContactsResponse:
    """Discover contacts at a company."""
    # Get company profile
    result = await db.execute(
        select(CompanyProfile).where(
            CompanyProfile.id == company_id,
            CompanyProfile.user_id == current_user.id,
            CompanyProfile.deleted_at.is_(None),
        )
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    # Log the start of contact discovery
    log_entry = AutomationLog(
        user_id=current_user.id,
        action_type="contact_discovery",
        entity_type="company",
        entity_id=company.id,
        status="started",
        details={"target_roles": request.roles, "limit": request.limit},
    )
    db.add(log_entry)
    await db.flush()

    # TODO: Integrate with actual contact discovery agent/service
    # For now, return existing contacts
    contacts_result = await db.execute(
        select(CompanyContact)
        .where(
            CompanyContact.company_profile_id == company_id,
            CompanyContact.user_id == current_user.id,
            CompanyContact.deleted_at.is_(None),
        )
        .order_by(CompanyContact.relevance_score.desc().nullslast())
        .limit(request.limit)
    )
    contacts = contacts_result.scalars().all()

    # Update log entry
    log_entry.status = "completed"
    log_entry.details = {
        "target_roles": request.roles,
        "limit": request.limit,
        "contacts_found": len(contacts),
    }
    await db.commit()

    logger.info(f"Found {len(contacts)} contacts for company {company_id} for user {current_user.id}")
    return FindContactsResponse(
        contacts_found=len(contacts),
        contacts=[CompanyContactResponse.model_validate(c) for c in contacts],
    )


@router.get("/outreach", response_model=NetworkingOutreachListResponse)
async def list_outreach(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = Query(
        None, alias="status", pattern="^(pending|draft_ready|sent|connected|no_response)$"
    ),
    channel: str | None = Query(None, pattern="^(linkedin|email)$"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> NetworkingOutreachListResponse:
    """List outreach draft messages."""
    query = select(NetworkingOutreach).where(
        NetworkingOutreach.user_id == current_user.id,
        NetworkingOutreach.deleted_at.is_(None),
    )

    if status_filter:
        query = query.where(NetworkingOutreach.status == OutreachStatus(status_filter.upper()))
    if channel:
        query = query.where(NetworkingOutreach.channel == channel)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get items with pagination
    query = query.order_by(NetworkingOutreach.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    outreach_items = result.scalars().all()

    return NetworkingOutreachListResponse(items=list(outreach_items), total=total)


@router.patch("/outreach/{outreach_id}", response_model=NetworkingOutreachResponse)
async def update_outreach(
    outreach_id: UUID,
    request: NetworkingOutreachUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NetworkingOutreach:
    """Edit an outreach draft message."""
    result = await db.execute(
        select(NetworkingOutreach).where(
            NetworkingOutreach.id == outreach_id,
            NetworkingOutreach.user_id == current_user.id,
            NetworkingOutreach.deleted_at.is_(None),
        )
    )
    outreach = result.scalar_one_or_none()

    if not outreach:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outreach not found")

    # Update fields if provided
    if request.status is not None:
        outreach.status = OutreachStatus(request.status.upper())
        if request.status == "sent":
            outreach.sent_at = datetime.now(timezone.utc)
    if request.subject is not None:
        outreach.subject = request.subject
    if request.message is not None:
        outreach.message = request.message

    await db.commit()
    await db.refresh(outreach)

    logger.info(f"Updated outreach {outreach_id} for user {current_user.id}")
    return outreach


# ============ Analytics Endpoints ============


@router.get("/stats", response_model=AutomationDashboard)
async def get_automation_stats(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AutomationDashboard:
    """Get dashboard metrics for automation features."""
    # Count active campaigns
    active_campaigns_result = await db.execute(
        select(func.count()).where(
            SearchCampaign.user_id == current_user.id,
            SearchCampaign.status == CampaignStatus.ACTIVE,
            SearchCampaign.deleted_at.is_(None),
        )
    )
    active_campaigns = active_campaigns_result.scalar() or 0

    # Count total discovered jobs
    total_jobs_result = await db.execute(
        select(func.count()).where(
            DiscoveredJob.user_id == current_user.id,
            DiscoveredJob.deleted_at.is_(None),
        )
    )
    total_jobs_discovered = total_jobs_result.scalar() or 0

    # Count pending applications (queued + resume_generated + applying)
    pending_statuses = [
        ApplicationStatus.QUEUED,
        ApplicationStatus.RESUME_GENERATED,
        ApplicationStatus.APPLYING,
    ]
    pending_result = await db.execute(
        select(func.count()).where(
            JobApplication.user_id == current_user.id,
            JobApplication.status.in_(pending_statuses),
            JobApplication.deleted_at.is_(None),
        )
    )
    pending_applications = pending_result.scalar() or 0

    # Count applications this week
    from datetime import timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    weekly_result = await db.execute(
        select(func.count()).where(
            JobApplication.user_id == current_user.id,
            JobApplication.applied_at >= week_ago,
            JobApplication.deleted_at.is_(None),
        )
    )
    applications_this_week = weekly_result.scalar() or 0

    # Calculate response rate
    applied_count_result = await db.execute(
        select(func.count()).where(
            JobApplication.user_id == current_user.id,
            JobApplication.status.in_([
                ApplicationStatus.APPLIED,
                ApplicationStatus.VIEWED,
                ApplicationStatus.RESPONSE_RECEIVED,
                ApplicationStatus.INTERVIEW_SCHEDULED,
                ApplicationStatus.REJECTED,
                ApplicationStatus.OFFER_RECEIVED,
            ]),
            JobApplication.deleted_at.is_(None),
        )
    )
    applied_count = applied_count_result.scalar() or 0

    response_count_result = await db.execute(
        select(func.count()).where(
            JobApplication.user_id == current_user.id,
            JobApplication.status.in_([
                ApplicationStatus.RESPONSE_RECEIVED,
                ApplicationStatus.INTERVIEW_SCHEDULED,
                ApplicationStatus.REJECTED,
                ApplicationStatus.OFFER_RECEIVED,
            ]),
            JobApplication.deleted_at.is_(None),
        )
    )
    response_count = response_count_result.scalar() or 0
    response_rate = (response_count / applied_count * 100) if applied_count > 0 else 0.0

    # Calculate interview rate
    interview_count_result = await db.execute(
        select(func.count()).where(
            JobApplication.user_id == current_user.id,
            JobApplication.status.in_([
                ApplicationStatus.INTERVIEW_SCHEDULED,
                ApplicationStatus.OFFER_RECEIVED,
            ]),
            JobApplication.deleted_at.is_(None),
        )
    )
    interview_count = interview_count_result.scalar() or 0
    interview_rate = (interview_count / applied_count * 100) if applied_count > 0 else 0.0

    # Get pipeline stats
    pipeline_stats = ApplicationPipelineStats()
    for status_enum in ApplicationStatus:
        count_result = await db.execute(
            select(func.count()).where(
                JobApplication.user_id == current_user.id,
                JobApplication.status == status_enum,
                JobApplication.deleted_at.is_(None),
            )
        )
        count = count_result.scalar() or 0
        setattr(pipeline_stats, status_enum.value, count)

    return AutomationDashboard(
        active_campaigns=active_campaigns,
        total_jobs_discovered=total_jobs_discovered,
        pending_applications=pending_applications,
        applications_this_week=applications_this_week,
        response_rate=round(response_rate, 2),
        interview_rate=round(interview_rate, 2),
        pipeline_stats=pipeline_stats,
    )


@router.get("/logs", response_model=AutomationLogListResponse)
async def get_automation_logs(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    action_type: str | None = Query(None, description="Filter by action type"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> AutomationLogListResponse:
    """Get audit logs for automation actions."""
    query = select(AutomationLog).where(AutomationLog.user_id == current_user.id)

    if action_type:
        query = query.where(AutomationLog.action_type == action_type)
    if entity_type:
        query = query.where(AutomationLog.entity_type == entity_type)
    if status_filter:
        query = query.where(AutomationLog.status == status_filter)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get items with pagination
    query = query.order_by(AutomationLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()

    return AutomationLogListResponse(items=list(logs), total=total)


# ============ Cron Job Management Endpoints ============
# Import cron job related modules

from src.core.scheduler import CronJobType, get_scheduler
from src.models.schemas.execution import (
    CronJobConfig,
    CronJobListResponse,
    CronJobResponse,
    CronJobSchedule,
    CronJobStatus as SchemaCronJobStatus,
    CronJobType as SchemaCronJobType,
)


@router.get("/cron/jobs", response_model=CronJobListResponse, tags=["Cron Jobs"])
async def list_cron_jobs(
    current_user: CurrentUser,
) -> CronJobListResponse:
    """List all cron jobs and their status.

    Returns the status of all automation cron jobs including:
    - Job discovery (every 4 hours)
    - Job analysis (every 1 hour)
    - Application queue processing (continuous with delays)
    """
    scheduler = get_scheduler()
    jobs = scheduler.get_all_job_statuses()

    return CronJobListResponse(
        items=[
            CronJobResponse(
                job_type=SchemaCronJobType(job["job_type"]),
                status=SchemaCronJobStatus(job["status"]),
                interval_seconds=job["interval_seconds"],
                last_run_at=datetime.fromisoformat(job["last_run_at"]) if job["last_run_at"] else None,
                next_run_at=datetime.fromisoformat(job["next_run_at"]) if job["next_run_at"] else None,
                last_run_status=job["last_run_status"],
                last_run_duration_ms=job["last_run_duration_ms"],
                run_count=job["run_count"],
                error_count=job.get("error_count", 0),
                config=job["config"],
            )
            for job in jobs
        ]
    )


@router.get("/cron/jobs/{job_type}", response_model=CronJobResponse, tags=["Cron Jobs"])
async def get_cron_job(
    job_type: SchemaCronJobType,
    current_user: CurrentUser,
) -> CronJobResponse:
    """Get detailed status of a specific cron job."""
    scheduler = get_scheduler()

    try:
        job_state = scheduler.get_job_status(CronJobType(job_type.value))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown job type: {job_type}",
        )

    if not job_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_type}",
        )

    job_dict = job_state.to_dict()
    return CronJobResponse(
        job_type=SchemaCronJobType(job_dict["job_type"]),
        status=SchemaCronJobStatus(job_dict["status"]),
        interval_seconds=job_dict["interval_seconds"],
        last_run_at=datetime.fromisoformat(job_dict["last_run_at"]) if job_dict["last_run_at"] else None,
        next_run_at=datetime.fromisoformat(job_dict["next_run_at"]) if job_dict["next_run_at"] else None,
        last_run_status=job_dict["last_run_status"],
        last_run_duration_ms=job_dict["last_run_duration_ms"],
        run_count=job_dict["run_count"],
        error_count=job_state.error_count,
        config=job_dict["config"],
    )


@router.post("/cron/jobs/{job_type}/pause", response_model=CronJobResponse, tags=["Cron Jobs"])
async def pause_cron_job(
    job_type: SchemaCronJobType,
    current_user: CurrentUser,
) -> CronJobResponse:
    """Pause a running cron job."""
    scheduler = get_scheduler()

    try:
        job_state = await scheduler.pause_job(CronJobType(job_type.value))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    job_dict = job_state.to_dict()
    logger.info(f"User {current_user.id} paused cron job {job_type.value}")
    return CronJobResponse(
        job_type=SchemaCronJobType(job_dict["job_type"]),
        status=SchemaCronJobStatus(job_dict["status"]),
        interval_seconds=job_dict["interval_seconds"],
        last_run_at=datetime.fromisoformat(job_dict["last_run_at"]) if job_dict["last_run_at"] else None,
        next_run_at=datetime.fromisoformat(job_dict["next_run_at"]) if job_dict["next_run_at"] else None,
        last_run_status=job_dict["last_run_status"],
        last_run_duration_ms=job_dict["last_run_duration_ms"],
        run_count=job_dict["run_count"],
        error_count=job_state.error_count,
        config=job_dict["config"],
    )


@router.post("/cron/jobs/{job_type}/resume", response_model=CronJobResponse, tags=["Cron Jobs"])
async def resume_cron_job(
    job_type: SchemaCronJobType,
    current_user: CurrentUser,
) -> CronJobResponse:
    """Resume a paused cron job."""
    scheduler = get_scheduler()

    try:
        job_state = await scheduler.resume_job(CronJobType(job_type.value))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    job_dict = job_state.to_dict()
    logger.info(f"User {current_user.id} resumed cron job {job_type.value}")
    return CronJobResponse(
        job_type=SchemaCronJobType(job_dict["job_type"]),
        status=SchemaCronJobStatus(job_dict["status"]),
        interval_seconds=job_dict["interval_seconds"],
        last_run_at=datetime.fromisoformat(job_dict["last_run_at"]) if job_dict["last_run_at"] else None,
        next_run_at=datetime.fromisoformat(job_dict["next_run_at"]) if job_dict["next_run_at"] else None,
        last_run_status=job_dict["last_run_status"],
        last_run_duration_ms=job_dict["last_run_duration_ms"],
        run_count=job_dict["run_count"],
        error_count=job_state.error_count,
        config=job_dict["config"],
    )


@router.post("/cron/jobs/{job_type}/trigger", response_model=CronJobResponse, tags=["Cron Jobs"])
async def trigger_cron_job(
    job_type: SchemaCronJobType,
    current_user: CurrentUser,
) -> CronJobResponse:
    """Manually trigger immediate execution of a cron job."""
    scheduler = get_scheduler()

    try:
        job_state = await scheduler.trigger_job(CronJobType(job_type.value))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    job_dict = job_state.to_dict()
    logger.info(f"User {current_user.id} manually triggered cron job {job_type.value}")
    return CronJobResponse(
        job_type=SchemaCronJobType(job_dict["job_type"]),
        status=SchemaCronJobStatus(job_dict["status"]),
        interval_seconds=job_dict["interval_seconds"],
        last_run_at=datetime.fromisoformat(job_dict["last_run_at"]) if job_dict["last_run_at"] else None,
        next_run_at=datetime.fromisoformat(job_dict["next_run_at"]) if job_dict["next_run_at"] else None,
        last_run_status=job_dict["last_run_status"],
        last_run_duration_ms=job_dict["last_run_duration_ms"],
        run_count=job_dict["run_count"],
        error_count=job_state.error_count,
        config=job_dict["config"],
    )


@router.put("/cron/jobs/{job_type}/config", response_model=CronJobResponse, tags=["Cron Jobs"])
async def update_cron_job_config(
    job_type: SchemaCronJobType,
    config: CronJobConfig,
    current_user: CurrentUser,
) -> CronJobResponse:
    """Update the configuration of a cron job."""
    scheduler = get_scheduler()

    try:
        job_state = await scheduler.update_job_config(
            CronJobType(job_type.value),
            interval_seconds=config.interval_seconds,
            config=config.config,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    job_dict = job_state.to_dict()
    logger.info(f"User {current_user.id} updated config for cron job {job_type.value}")
    return CronJobResponse(
        job_type=SchemaCronJobType(job_dict["job_type"]),
        status=SchemaCronJobStatus(job_dict["status"]),
        interval_seconds=job_dict["interval_seconds"],
        last_run_at=datetime.fromisoformat(job_dict["last_run_at"]) if job_dict["last_run_at"] else None,
        next_run_at=datetime.fromisoformat(job_dict["next_run_at"]) if job_dict["next_run_at"] else None,
        last_run_status=job_dict["last_run_status"],
        last_run_duration_ms=job_dict["last_run_duration_ms"],
        run_count=job_dict["run_count"],
        error_count=job_state.error_count,
        config=job_dict["config"],
    )


@router.get("/cron/schedule", response_model=CronJobSchedule, tags=["Cron Jobs"])
async def get_cron_schedule(
    current_user: CurrentUser,
) -> CronJobSchedule:
    """Get the current schedule configuration for all cron jobs."""
    scheduler = get_scheduler()

    discovery = scheduler.get_job_status(CronJobType.JOB_DISCOVERY)
    analysis = scheduler.get_job_status(CronJobType.JOB_ANALYSIS)
    queue = scheduler.get_job_status(CronJobType.APPLICATION_QUEUE)

    return CronJobSchedule(
        job_discovery_interval_hours=discovery.interval_seconds // 3600 if discovery else 4,
        job_analysis_interval_hours=analysis.interval_seconds // 3600 if analysis else 1,
        application_queue_delay_seconds=queue.interval_seconds if queue else 30,
        application_queue_batch_size=queue._config.get("batch_size", 5) if queue else 5,
    )


@router.put("/cron/schedule", response_model=CronJobSchedule, tags=["Cron Jobs"])
async def update_cron_schedule(
    schedule: CronJobSchedule,
    current_user: CurrentUser,
) -> CronJobSchedule:
    """Update the schedule configuration for all cron jobs.

    This allows updating all job schedules at once:
    - Job discovery interval (in hours)
    - Job analysis interval (in hours)
    - Application queue processing delay (in seconds)
    - Application queue batch size
    """
    scheduler = get_scheduler()

    # Update job discovery
    await scheduler.update_job_config(
        CronJobType.JOB_DISCOVERY,
        interval_seconds=schedule.job_discovery_interval_hours * 3600,
    )

    # Update job analysis
    await scheduler.update_job_config(
        CronJobType.JOB_ANALYSIS,
        interval_seconds=schedule.job_analysis_interval_hours * 3600,
    )

    # Update application queue
    await scheduler.update_job_config(
        CronJobType.APPLICATION_QUEUE,
        interval_seconds=schedule.application_queue_delay_seconds,
        config={"batch_size": schedule.application_queue_batch_size},
    )

    logger.info(f"User {current_user.id} updated cron schedule")
    return schedule


# ============ Execution Monitoring Endpoints ============
# Include execution router for workflow monitoring

from src.api.routes.execution import router as execution_router

router.include_router(
    execution_router,
    prefix="/executions",
    tags=["Executions"],
)
