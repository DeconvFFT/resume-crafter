"""Background tasks for job description analysis."""

import logging
from uuid import UUID

import httpx
from sqlalchemy import select

from src.models.database import (
    JobDescription,
    JobRequirement,
    RequirementType,
    TaskStatus,
)
from src.parsers.html_parser import HTMLParser

logger = logging.getLogger(__name__)


async def analyze_job(
    ctx: dict,
    job_id: UUID,
    user_id: UUID,
) -> dict:
    """Analyze a job description: fetch URL, extract requirements, generate embeddings.

    Args:
        ctx: ARQ context with db_session_factory and services.
        job_id: ID of the job to analyze.
        user_id: ID of the job owner.

    Returns:
        Analysis result with status and extracted data.
    """
    db_session_factory = ctx["db_session_factory"]
    embedding_service = ctx["embedding_service"]

    async with db_session_factory() as db:
        try:
            # Get job
            result = await db.execute(
                select(JobDescription).where(
                    JobDescription.id == job_id,
                    JobDescription.user_id == user_id,
                )
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.error(f"Job {job_id} not found")
                return {"status": "error", "message": "Job not found"}

            # Update status to processing
            job.processing_status = TaskStatus.PROCESSING
            await db.commit()

            # Step 1: Fetch content if URL provided
            scraped_title = None
            scraped_company = None
            if job.source_url and not job.raw_text:
                raw_text, scraped_title, scraped_company = await _fetch_job_content(job.source_url)
                job.raw_text = raw_text
                await db.commit()

            if not job.raw_text:
                job.processing_status = TaskStatus.FAILED
                job.processing_error = "No job description content available"
                await db.commit()
                return {"status": "error", "message": "No content available"}

            # Step 2: Extract job details and requirements
            from src.core.llm_client import get_llm_client
            llm = get_llm_client()

            extraction = await llm.extract_job_requirements(job.raw_text)

            # Update job metadata (use LLM extraction, fallback to scraped values)
            job.company = extraction.company or scraped_company
            job.role = extraction.role or scraped_title
            job.location = extraction.location
            job.salary_range = extraction.salary_range
            job.experience_level = extraction.experience_level
            await db.commit()

            # Step 3: Create requirements with embeddings
            # Validate that we actually extracted requirements
            if not extraction.requirements:
                logger.warning(
                    f"Job {job_id}: No requirements extracted from job description. "
                    f"Company: {extraction.company}, Role: {extraction.role}"
                )
                job.processing_status = TaskStatus.FAILED
                job.processing_error = (
                    "Unable to extract requirements from job description. "
                    "The job posting may be too short, unclear, or in an unsupported format. "
                    "Please try pasting the job description directly."
                )
                await db.commit()
                return {
                    "status": "error",
                    "message": "No requirements could be extracted from the job description",
                    "company": extraction.company,
                    "role": extraction.role,
                }

            req_index = 0
            for req_data in extraction.requirements:
                # Generate embedding for the requirement
                embedding = await embedding_service.embed_single(req_data.content)
                embedding_id = f"job_req_{job_id}_{req_index}"

                # Store in ChromaDB (TODO: implement vector store)
                # await vector_store.add(embedding_id, embedding, {"type": "job_requirement"})

                requirement = JobRequirement(
                    job_id=job.id,
                    content=req_data.content,
                    requirement_type=RequirementType(req_data.requirement_type),
                    importance_score=req_data.importance,
                    keywords=req_data.keywords,
                    embedding_id=embedding_id,
                )
                db.add(requirement)
                req_index += 1

            # Mark as completed - we have validated requirements exist
            job.processing_status = TaskStatus.COMPLETED
            await db.commit()

            logger.info(
                f"Job {job_id} analyzed: {extraction.company} - {extraction.role}, "
                f"{len(extraction.requirements)} requirements extracted"
            )

            return {
                "status": "success",
                "company": extraction.company,
                "role": extraction.role,
                "requirements_count": len(extraction.requirements),
            }

        except Exception as e:
            logger.exception(f"Error analyzing job {job_id}: {e}")

            # Update job status
            job.processing_status = TaskStatus.FAILED
            job.processing_error = str(e)
            await db.commit()

            return {"status": "error", "message": str(e)}


async def _fetch_job_content(url: str) -> tuple[str, str | None, str | None]:
    """Fetch and parse job description from URL with Playwright fallback.

    Args:
        url: Job posting URL.

    Returns:
        Tuple of (text, title, company) extracted from job posting.
    """
    try:
        from src.integrations.job_scraper import scrape_job_url

        result = await scrape_job_url(url)
        return result.text, result.title, result.company

    except Exception as e:
        logger.warning(f"Job scraper failed for {url}: {e}, trying basic HTTP")

        # Fallback to basic HTTP
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()

                html_content = response.text
                text = HTMLParser.parse(html_content, convert_to_markdown=True)
                return text, None, None

            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch job URL {url}: {e}")
                raise ValueError(f"Failed to fetch job posting: {e}") from e
