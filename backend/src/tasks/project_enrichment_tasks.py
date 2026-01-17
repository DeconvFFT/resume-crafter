"""Background tasks for project enrichment via GitHub API with real-time SSE updates."""

import logging
from dataclasses import asdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.database import Project, ProjectBullet, ProjectLink, LinkType, TaskStatus, BackgroundTask
from src.core.pubsub import publish_log, publish_status, publish_done, publish_error

logger = logging.getLogger(__name__)


async def _publish_enrichment_event(
    project_id: UUID,
    step: str,
    status: str,
    message: str,
    details: dict | None = None,
) -> None:
    """Publish an SSE event for project enrichment progress.

    Args:
        project_id: Project being enriched.
        step: Current step name.
        status: Step status.
        message: Human-readable message.
        details: Optional additional details.
    """
    try:
        # Use project_id as document_id for the SSE channel
        # The frontend can subscribe to project-specific updates
        await publish_log(
            document_id=project_id,  # Reuse document channel for project updates
            step=f"github_enrichment:{step}",
            status=status,
            message=message,
            details=details,
        )
    except Exception as e:
        logger.debug(f"Failed to publish enrichment event: {e}")


async def _update_background_task_status(
    db,
    user_id: UUID,
    project_id: UUID,
    status: TaskStatus,
    error: str | None = None,
    progress: int = 0,
) -> None:
    """Update the background task record for this enrichment.

    Args:
        db: Database session.
        user_id: Owner user ID.
        project_id: Project being enriched.
        status: New status.
        error: Error message if failed.
        progress: Progress percentage (0-100).
    """
    try:
        result = await db.execute(
            select(BackgroundTask).where(
                BackgroundTask.user_id == user_id,
                BackgroundTask.entity_id == project_id,
                BackgroundTask.task_type == "enrich_project",
            ).order_by(BackgroundTask.created_at.desc()).limit(1)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = status
            task.progress = progress
            if error:
                task.error_message = error
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to update background task status: {e}")


async def enrich_project_from_github(
    ctx: dict,
    project_id: UUID,
    user_id: UUID,
    github_url: str,
) -> dict:
    """Enrich a project with data from GitHub.

    This is a multi-agent pipeline:
    1. Agent 1 (GitHub Service): Fetches repository data from GitHub API
    2. Agent 2 (LLM): Analyzes and understands the project
    3. Agent 3 (LLM): Generates resume-ready bullet points

    Args:
        ctx: ARQ context with db_session_factory and services.
        project_id: ID of the project to enrich.
        user_id: ID of the project owner.
        github_url: GitHub repository URL.

    Returns:
        Enrichment result with status and generated data.
    """
    db_session_factory = ctx["db_session_factory"]
    embedding_service = ctx["embedding_service"]

    async with db_session_factory() as db:
        try:
            # Get project with eagerly loaded relationships to avoid greenlet issues
            result = await db.execute(
                select(Project)
                .options(selectinload(Project.bullets), selectinload(Project.links))
                .where(
                    Project.id == project_id,
                    Project.user_id == user_id,
                )
            )
            project = result.scalar_one_or_none()

            if not project:
                logger.error(f"Project {project_id} not found")
                return {"status": "error", "message": "Project not found"}

            # Update task status to processing
            await _update_background_task_status(db, user_id, project_id, TaskStatus.PROCESSING, progress=10)

            logger.info(f"Starting GitHub enrichment for project {project_id}: {github_url}")

            # Publish SSE event for start
            await _publish_enrichment_event(
                project_id, "start", "started",
                f"Starting GitHub enrichment for {project.name}",
                {"github_url": github_url, "project_name": project.name}
            )

            # ============ AGENT 1: Fetch GitHub Data ============
            from src.integrations.github import GitHubService
            from src.config import get_settings

            settings = get_settings()
            github_token = getattr(settings, 'github_token', None)

            github_service = GitHubService(token=github_token)
            await _publish_enrichment_event(
                project_id, "fetch_github", "started",
                "Fetching repository data from GitHub API..."
            )

            try:
                repo_info = await github_service.fetch_repo_from_url(github_url)
                if not repo_info:
                    error_msg = f"Could not fetch GitHub repository: {github_url}"
                    logger.error(f"Project {project_id}: {error_msg}")
                    await _publish_enrichment_event(
                        project_id, "fetch_github", "failed",
                        "Failed to fetch repository - check if URL is correct and repo is public"
                    )
                    await _update_background_task_status(
                        db, user_id, project_id, TaskStatus.FAILED,
                        error=f"GitHub API error: Unable to fetch repository. Check if the URL is correct and the repository is public.",
                    )
                    return {"status": "error", "message": error_msg}

                logger.info(
                    f"Agent 1 complete: Fetched {repo_info.full_name} "
                    f"({repo_info.stars} stars, {repo_info.commits_count} commits)"
                )
                await _publish_enrichment_event(
                    project_id, "fetch_github", "completed",
                    f"Fetched {repo_info.full_name}: {repo_info.stars} stars, {repo_info.commits_count} commits",
                    {
                        "repo_name": repo_info.full_name,
                        "stars": repo_info.stars,
                        "commits": repo_info.commits_count,
                        "languages": list(repo_info.languages.keys())[:5] if repo_info.languages else [],
                    }
                )
                await _update_background_task_status(db, user_id, project_id, TaskStatus.PROCESSING, progress=30)
            except Exception as github_error:
                error_msg = f"GitHub API error: {str(github_error)}"
                logger.error(f"Project {project_id}: {error_msg}")
                await _update_background_task_status(
                    db, user_id, project_id, TaskStatus.FAILED,
                    error=error_msg,
                )
                return {"status": "error", "message": error_msg}
            finally:
                await github_service.close()

            # ============ AGENT 2: Understand Project ============
            from src.core.llm_client import get_llm_client

            await _publish_enrichment_event(
                project_id, "analyze_project", "started",
                "AI is analyzing the repository structure and code..."
            )

            llm = get_llm_client()

            # Convert dataclass to dict for LLM
            repo_dict = asdict(repo_info)
            understanding = await llm.understand_github_project(repo_dict)

            logger.info(
                f"Agent 2 complete: Identified as {understanding.project_type}, "
                f"complexity: {understanding.complexity_level}, "
                f"{len(understanding.key_features)} features"
            )
            await _publish_enrichment_event(
                project_id, "analyze_project", "completed",
                f"Identified {understanding.project_type} project ({understanding.complexity_level} complexity)",
                {
                    "project_type": understanding.project_type,
                    "complexity": understanding.complexity_level,
                    "features_count": len(understanding.key_features),
                    "key_features": understanding.key_features[:3] if understanding.key_features else [],
                }
            )
            await _update_background_task_status(db, user_id, project_id, TaskStatus.PROCESSING, progress=60)

            # ============ AGENT 3: Generate Resume Bullets ============
            await _publish_enrichment_event(
                project_id, "generate_bullets", "started",
                "AI is crafting impactful resume bullet points..."
            )

            enrichment = await llm.generate_project_bullets(
                understanding,
                existing_description=project.description,
            )

            logger.info(
                f"Agent 3 complete: Generated {len(enrichment.enriched_bullets)} bullets "
                f"(confidence: {enrichment.confidence:.0%})"
            )
            await _publish_enrichment_event(
                project_id, "generate_bullets", "completed",
                f"Generated {len(enrichment.enriched_bullets)} resume bullet points",
                {
                    "bullets_count": len(enrichment.enriched_bullets),
                    "confidence": enrichment.confidence,
                    "suggested_technologies": enrichment.suggested_technologies[:5] if enrichment.suggested_technologies else [],
                }
            )
            await _update_background_task_status(db, user_id, project_id, TaskStatus.PROCESSING, progress=80)

            # ============ Update Project with Enriched Data ============

            # Update project description if suggested title is better
            if enrichment.suggested_title and not project.name.strip():
                project.name = enrichment.suggested_title

            # Update description with summary
            if enrichment.project_summary:
                project.description = enrichment.project_summary

            # Update technologies
            if enrichment.suggested_technologies:
                existing_techs = set(project.technologies or [])
                new_techs = set(enrichment.suggested_technologies)
                project.technologies = list(existing_techs | new_techs)

            # Store existing bullets and links before commit (they're eagerly loaded)
            existing_bullets = list(project.bullets)
            existing_links = list(project.links)
            existing_bullet_count = len(existing_bullets)

            await db.commit()

            # Add enriched bullets (prepend to existing, maintaining order)
            for idx, bullet_data in enumerate(enrichment.enriched_bullets):
                # Skip embedding generation for now - fix greenlet issue later
                # TODO: Re-enable embedding after fixing async/sync issue
                # embedding = await embedding_service.embed_single(bullet_data.content)
                embedding_id = f"proj_bullet_{project.id}_enriched_{idx}"

                bullet = ProjectBullet(
                    project_id=project.id,
                    content=bullet_data.content,
                    order_index=idx,  # Put enriched bullets first
                    skills=bullet_data.skills,
                    metrics=bullet_data.metrics,
                    embedding_id=embedding_id,
                )
                db.add(bullet)

            # Re-order existing bullets to come after enriched ones
            for i, existing_bullet in enumerate(existing_bullets):
                # Re-attach to session since commit expired objects
                db.add(existing_bullet)
                existing_bullet.order_index = len(enrichment.enriched_bullets) + i

            # Ensure GitHub link is stored
            has_github_link = any(
                link.link_type == LinkType.GITHUB
                for link in existing_links
            )
            if not has_github_link:
                github_link = ProjectLink(
                    project_id=project.id,
                    url=github_url,
                    link_type=LinkType.GITHUB,
                    title=repo_info.full_name,
                )
                db.add(github_link)

            await db.commit()

            logger.info(
                f"Project {project_id} enriched successfully: "
                f"{len(enrichment.enriched_bullets)} new bullets added"
            )

            # Mark task as completed and publish completion event
            await _update_background_task_status(db, user_id, project_id, TaskStatus.COMPLETED, progress=100)
            await publish_done(
                document_id=project_id,
                result={"message": f"GitHub enrichment complete: {len(enrichment.enriched_bullets)} bullet points added"},
            )

            return {
                "status": "success",
                "bullets_added": len(enrichment.enriched_bullets),
                "project_type": understanding.project_type,
                "complexity": understanding.complexity_level,
                "confidence": enrichment.confidence,
                "technologies": enrichment.suggested_technologies,
            }

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Error enriching project {project_id}: {error_msg}")

            # Update task status to failed with error message
            await _update_background_task_status(
                db, user_id, project_id, TaskStatus.FAILED,
                error=f"Enrichment failed: {error_msg}",
            )

            # Publish error event
            await publish_error(
                document_id=project_id,
                error=f"GitHub enrichment failed: {error_msg}",
            )

            return {"status": "error", "message": error_msg}
