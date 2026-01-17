"""Background tasks for document processing with checkpoint support and real-time streaming.

Provides resumable document processing using CheckpointManager. If processing
is interrupted (SIGTERM, timeout, error), it can resume from the last
successful checkpoint instead of starting over.

Real-time updates are published via Redis Pub/Sub for SSE streaming to clients.
"""

import asyncio
import logging
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select

from src.models.database import (
    Document,
    DocumentClass,
    Experience,
    ExperienceBullet,
    Project,
    ProjectBullet,
    ProjectLink,
    LinkType,
    TaskStatus,
    BackgroundTask,
    Skill,
    SkillCategory,
    ProficiencyLevel,
    Publication,
    PublicationType,
)
from src.tasks.checkpoint import (
    CheckpointManager,
    ProcessingStep,
    restore_classification_from_checkpoint,
)
from src.tasks.shutdown import (
    register_checkpoint_manager,
    unregister_checkpoint_manager,
    is_shutdown_requested,
)
from src.core.pubsub import (
    publish_log,
    publish_thinking,
    publish_status,
    publish_done,
    publish_error,
)
from src.config import get_settings

logger = logging.getLogger(__name__)


async def _store_bullet_in_vector_store(
    vector_store,
    embedding_id: str,
    embedding: list[float],
    content: str,
    user_id: UUID,
    bullet_id: UUID,
    document_id: UUID,
    bullet_type: str,
) -> bool:
    """Store a bullet embedding in ChromaDB.

    Args:
        vector_store: VectorStore instance (may be None).
        embedding_id: Unique ID for the embedding.
        embedding: The embedding vector.
        content: The bullet text content.
        user_id: Owner user ID.
        bullet_id: The bullet's database ID.
        document_id: Source document ID.
        bullet_type: Type of bullet ("experience" or "project").

    Returns:
        True if stored successfully, False otherwise.
    """
    if vector_store is None:
        return False

    try:
        await vector_store.add(
            id=embedding_id,
            embedding=embedding,
            document=content,
            metadata={
                "user_id": str(user_id),
                "bullet_id": str(bullet_id),
                "document_id": str(document_id),
                "type": bullet_type,
            },
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to store bullet {embedding_id} in vector store: {e}")
        return False


async def _store_bullets_batch_in_vector_store(
    vector_store,
    bullets_data: list[dict],
) -> int:
    """Store multiple bullet embeddings in ChromaDB as a batch.

    Args:
        vector_store: VectorStore instance (may be None).
        bullets_data: List of dicts with keys: embedding_id, embedding, content,
                      user_id, bullet_id, document_id, bullet_type.

    Returns:
        Number of bullets stored successfully.
    """
    if vector_store is None or not bullets_data:
        return 0

    try:
        ids = [b["embedding_id"] for b in bullets_data]
        embeddings = [b["embedding"] for b in bullets_data]
        documents = [b["content"] for b in bullets_data]
        metadatas = [
            {
                "user_id": str(b["user_id"]),
                "bullet_id": str(b["bullet_id"]),
                "document_id": str(b["document_id"]),
                "type": b["bullet_type"],
            }
            for b in bullets_data
        ]

        await vector_store.add_batch(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        logger.debug(f"Stored {len(bullets_data)} bullets in vector store")
        return len(bullets_data)
    except Exception as e:
        logger.warning(f"Failed to batch store bullets in vector store: {e}")
        return 0


async def _store_supervisor_results(
    db,
    embedding_service,
    vector_store,
    document: Document,
    user_id: UUID,
    supervisor_result,
) -> dict:
    """Store extraction results from Supervisor to database.

    Args:
        db: Database session.
        embedding_service: Embedding service.
        vector_store: VectorStore instance (may be None).
        document: Source document.
        user_id: Owner user ID.
        supervisor_result: SupervisorResult from Supervisor.process().

    Returns:
        dict with extraction counts.
    """
    from src.agents import SupervisorResult
    from sqlalchemy import select

    counts = {
        "experiences": 0,
        "projects": 0,
        "skills": 0,
        "publications": 0,
    }
    bullets_for_vector_store = []

    # ========== Store Experiences ==========
    if supervisor_result.experiences and supervisor_result.experiences.experiences:
        skipped_count = 0
        for exp_data in supervisor_result.experiences.experiences:
            # Post-extraction validation: skip entries that look like projects
            if _is_likely_project_not_experience(exp_data.company, exp_data.role):
                logger.info(
                    f"Skipping project-like entry: {exp_data.company} - {exp_data.role}"
                )
                skipped_count += 1
                continue

            start_date = _parse_date(exp_data.start_date)
            end_date = _parse_date(exp_data.end_date) if exp_data.end_date else None

            experience = Experience(
                user_id=user_id,
                source_document_id=document.id,
                company=exp_data.company,
                role=exp_data.role,
                location=exp_data.location,
                start_date=start_date,
                end_date=end_date,
                is_current=exp_data.is_current,
            )
            db.add(experience)
            await db.flush()

            for idx, bullet_data in enumerate(exp_data.bullets):
                embedding = await embedding_service.embed_single(bullet_data.content)
                embedding_id = f"exp_bullet_{experience.id}_{idx}"

                bullet = ExperienceBullet(
                    experience_id=experience.id,
                    content=bullet_data.content,
                    order_index=idx,
                    skills=bullet_data.skills,
                    metrics=bullet_data.metrics,
                    action_verbs=bullet_data.action_verbs,
                    embedding_id=embedding_id,
                )
                db.add(bullet)
                await db.flush()

                bullets_for_vector_store.append({
                    "embedding_id": embedding_id,
                    "embedding": embedding,
                    "content": bullet_data.content,
                    "user_id": user_id,
                    "bullet_id": bullet.id,
                    "document_id": document.id,
                    "bullet_type": "experience",
                })

            await db.commit()

        counts["experiences"] = len(supervisor_result.experiences.experiences) - skipped_count

    # ========== Store Projects ==========
    if supervisor_result.projects and supervisor_result.projects.projects:
        projects_to_enrich = []

        for proj_data in supervisor_result.projects.projects:
            start_date = _parse_date(proj_data.start_date) if proj_data.start_date else None
            end_date = _parse_date(proj_data.end_date) if proj_data.end_date else None

            project = Project(
                user_id=user_id,
                source_document_id=document.id,
                name=proj_data.name,
                description=proj_data.description,
                technologies=proj_data.technologies,
                start_date=start_date,
                end_date=end_date,
            )
            db.add(project)
            await db.flush()

            for idx, bullet_data in enumerate(proj_data.bullets):
                embedding = await embedding_service.embed_single(bullet_data.content)
                embedding_id = f"proj_bullet_{project.id}_{idx}"

                bullet = ProjectBullet(
                    project_id=project.id,
                    content=bullet_data.content,
                    order_index=idx,
                    skills=bullet_data.skills,
                    metrics=bullet_data.metrics,
                    embedding_id=embedding_id,
                )
                db.add(bullet)
                await db.flush()

                bullets_for_vector_store.append({
                    "embedding_id": embedding_id,
                    "embedding": embedding,
                    "content": bullet_data.content,
                    "user_id": user_id,
                    "bullet_id": bullet.id,
                    "document_id": document.id,
                    "bullet_type": "project",
                })

            # Add links and track GitHub for enrichment
            github_url = None
            for link_data in proj_data.links:
                url = link_data.get("url", "")
                if not _is_valid_url(url):
                    continue

                link_type = _map_link_type(link_data.get("type", "other"))
                link = ProjectLink(
                    project_id=project.id,
                    url=url,
                    link_type=link_type,
                    title=link_data.get("title"),
                )
                db.add(link)

                if link_type == LinkType.GITHUB and not github_url:
                    github_url = url

            await db.commit()

            if github_url:
                projects_to_enrich.append((project.id, github_url))

        counts["projects"] = len(supervisor_result.projects.projects)

        # Queue GitHub enrichment for projects with links
        if projects_to_enrich:
            await _enqueue_project_enrichments(db, user_id, projects_to_enrich)

    # ========== Store Skills ==========
    if supervisor_result.skills and supervisor_result.skills.skills:
        extracted_skills_count = len(supervisor_result.skills.skills)
        logger.info(f"Processing {extracted_skills_count} extracted skills")
        # Only check non-deleted skills for deduplication
        existing_result = await db.execute(
            select(Skill.name).where(
                Skill.user_id == user_id,
                Skill.deleted_at.is_(None)  # Exclude soft-deleted
            )
        )
        existing_skill_names = {name.lower() for name in existing_result.scalars().all()}
        skills_added = 0
        skills_skipped = 0

        for skill_data in supervisor_result.skills.skills:
            if skill_data.name.lower() in existing_skill_names:
                skills_skipped += 1
                continue

            skill = Skill(
                user_id=user_id,
                name=skill_data.name,
                category=_map_skill_category(skill_data.category),
                proficiency=_map_proficiency_level(skill_data.proficiency),
                years_of_experience=skill_data.years_experience,
                display_order=skills_added,
            )
            db.add(skill)
            skills_added += 1
            existing_skill_names.add(skill_data.name.lower())

        await db.commit()
        counts["skills"] = skills_added
        # Log extraction vs storage for debugging
        logger.info(
            f"Skills: extracted={extracted_skills_count}, "
            f"new={skills_added}, skipped_duplicates={skills_skipped}"
        )
    else:
        logger.warning(
            f"No skills to store: supervisor_result.skills={supervisor_result.skills is not None}, "
            f"skills_list={'non-empty' if supervisor_result.skills and supervisor_result.skills.skills else 'empty or None'}"
        )

    # ========== Store Publications (if any) ==========
    if supervisor_result.publications and supervisor_result.publications.publications:
        extracted_pubs_count = len(supervisor_result.publications.publications)
        # Only check non-deleted publications for deduplication
        existing_result = await db.execute(
            select(Publication.title).where(
                Publication.user_id == user_id,
                Publication.deleted_at.is_(None)  # Exclude soft-deleted
            )
        )
        existing_titles = {title.lower() for title in existing_result.scalars().all()}
        pubs_added = 0
        pubs_skipped = 0

        for pub_data in supervisor_result.publications.publications:
            if pub_data.title.lower() in existing_titles:
                pubs_skipped += 1
                continue

            pub_date = _parse_date(pub_data.publication_date) if pub_data.publication_date else None
            authors_str = ", ".join(pub_data.authors) if pub_data.authors else ""

            publication = Publication(
                user_id=user_id,
                source_document_id=document.id,
                title=pub_data.title,
                authors=authors_str,
                publication_type=_map_publication_type(pub_data.publication_type),
                venue=pub_data.venue,
                publication_date=pub_date,
                doi=pub_data.doi,
                url=pub_data.url,
                abstract=pub_data.abstract,
                is_first_author=pub_data.is_first_author,
                display_order=pubs_added,
            )
            db.add(publication)
            pubs_added += 1
            existing_titles.add(pub_data.title.lower())

        await db.commit()
        counts["publications"] = pubs_added
        # Log extraction vs storage for debugging
        logger.info(
            f"Publications: extracted={extracted_pubs_count}, "
            f"new={pubs_added}, skipped_duplicates={pubs_skipped}"
        )
    else:
        logger.warning(
            f"No publications to store: supervisor_result.publications={supervisor_result.publications is not None}, "
            f"pubs_list={'non-empty' if supervisor_result.publications and supervisor_result.publications.publications else 'empty or None'}"
        )

    # Batch store all bullets in vector store
    await _store_bullets_batch_in_vector_store(vector_store, bullets_for_vector_store)

    return counts


def _create_log_entry(step: str, status: str, message: str, details: dict | None = None) -> dict:
    """Create a structured log entry for COT display.

    Args:
        step: Processing step name (e.g., "classification", "extraction")
        status: Status of the step (e.g., "started", "completed", "thinking")
        message: Human-readable message
        details: Optional additional details

    Returns:
        Structured log entry dict.
    """
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "step": step,
        "status": status,
        "message": message,
    }
    if details:
        entry["details"] = details
    return entry


async def _add_processing_log(db, document: Document, log_entry: dict) -> None:
    """Add a log entry to the document's processing_logs and publish to Redis.

    This function both persists the log to the database (for later retrieval)
    and publishes it to Redis Pub/Sub for real-time SSE streaming.

    Args:
        db: Database session
        document: Document to update
        log_entry: Log entry to add
    """
    if document.processing_logs is None:
        document.processing_logs = []
    # Create a new list to trigger SQLAlchemy change detection
    new_logs = list(document.processing_logs)
    new_logs.append(log_entry)
    document.processing_logs = new_logs
    await db.commit()

    # Publish to Redis for real-time SSE streaming
    try:
        await publish_log(
            document_id=document.id,
            step=log_entry.get("step", "unknown"),
            status=log_entry.get("status", "info"),
            message=log_entry.get("message", ""),
            details=log_entry.get("details"),
        )
    except Exception as e:
        # Don't fail processing if publish fails
        logger.warning(f"Failed to publish log event for document {document.id}: {e}")


async def process_document(
    ctx: dict,
    document_id: UUID,
    user_id: UUID,
) -> dict:
    """Process an uploaded document with checkpoint support for resumable processing.

    Uses CheckpointManager to save progress after each pipeline step. If interrupted
    (SIGTERM, timeout, error), processing can resume from the last checkpoint.

    Args:
        ctx: ARQ context with db_session_factory and services.
        document_id: ID of the document to process.
        user_id: ID of the document owner.

    Returns:
        Processing result with status and extracted data.
    """
    db_session_factory = ctx["db_session_factory"]
    embedding_service = ctx["embedding_service"]
    vector_store = ctx.get("vector_store")  # May be None if ChromaDB unavailable

    async with db_session_factory() as db:
        checkpoint_manager = None
        try:
            # Get document
            result = await db.execute(
                select(Document).where(
                    Document.id == document_id,
                    Document.user_id == user_id,
                )
            )
            document = result.scalar_one_or_none()

            if not document:
                logger.error(f"Document {document_id} not found")
                return {"status": "error", "message": "Document not found"}

            # Initialize checkpoint manager and register for graceful shutdown
            checkpoint_manager = CheckpointManager(db, document)
            register_checkpoint_manager(document_id, checkpoint_manager)

            # Increment processing attempt counter
            attempt = await checkpoint_manager.increment_attempt()
            resume_step = checkpoint_manager.get_resume_step()
            is_resuming = checkpoint_manager.is_resuming()

            if is_resuming:
                logger.info(
                    f"Resuming document {document_id} from step {resume_step.value} "
                    f"(attempt {attempt})"
                )
                await _add_processing_log(db, document, _create_log_entry(
                    "init", "resumed",
                    f"Resuming processing from {resume_step.value} (attempt {attempt})",
                    {"resume_step": resume_step.value, "attempt": attempt}
                ))
            else:
                # Fresh start - initialize processing logs
                document.processing_logs = []
                document.processing_status = TaskStatus.PROCESSING
                await db.commit()

                await _add_processing_log(db, document, _create_log_entry(
                    "init", "started", f"Starting to process document: {document.filename}"
                ))

            # Publish status for SSE
            try:
                await publish_status(
                    document_id=document_id,
                    status="processing",
                    progress=0,
                )
            except Exception as e:
                logger.warning(f"Failed to publish initial status: {e}")

            # Get LLM client (needed for multiple steps)
            from src.core.llm_client import get_llm_client
            llm = get_llm_client()

            # Set up thinking callback for real-time CoT streaming
            async def thinking_callback(thinking_text: str, is_complete: bool) -> None:
                try:
                    await publish_thinking(document_id, thinking_text, is_complete)
                except Exception as e:
                    logger.warning(f"Failed to publish thinking event: {e}")

            llm.set_thinking_callback(lambda t, c: asyncio.create_task(thinking_callback(t, c)))

            # Track extraction counts (may be loaded from checkpoint)
            extraction_counts = checkpoint_manager.state.extraction_counts.copy()

            # Classification result - may be restored from checkpoint
            classification = None

            # ========== Step 1: Text Extraction ==========
            if not checkpoint_manager.state.is_step_completed(ProcessingStep.TEXT_EXTRACTION):
                # Check for shutdown before starting
                if is_shutdown_requested() or checkpoint_manager.shutdown_requested:
                    await checkpoint_manager.save_interrupt_state(
                        ProcessingStep.TEXT_EXTRACTION, "Shutdown requested before text extraction"
                    )
                    raise asyncio.CancelledError("Shutdown requested")

                if not document.raw_text:
                    await _add_processing_log(db, document, _create_log_entry(
                        "text_extraction", "started", "Extracting text from document..."
                    ))

                    raw_text = await _extract_text(document)
                    document.raw_text = raw_text
                    await db.commit()

                    await _add_processing_log(db, document, _create_log_entry(
                        "text_extraction", "completed",
                        f"Extracted {len(raw_text)} characters of text",
                        {"text_length": len(raw_text), "preview": raw_text[:200] + "..." if len(raw_text) > 200 else raw_text}
                    ))

                if not document.raw_text:
                    await _add_processing_log(db, document, _create_log_entry(
                        "text_extraction", "failed", "Could not extract any text from document"
                    ))
                    document.processing_status = TaskStatus.FAILED
                    document.processing_error = "Failed to extract text from document"
                    await db.commit()
                    return {"status": "error", "message": "Text extraction failed"}

                # Save checkpoint after successful text extraction
                await checkpoint_manager.save_checkpoint(ProcessingStep.TEXT_EXTRACTION)
                logger.debug(f"Checkpoint saved: TEXT_EXTRACTION for document {document_id}")

            # ========== Step 2: Classification ==========
            if not checkpoint_manager.state.is_step_completed(ProcessingStep.CLASSIFICATION):
                # Check for shutdown
                if is_shutdown_requested() or checkpoint_manager.shutdown_requested:
                    await checkpoint_manager.save_interrupt_state(
                        ProcessingStep.CLASSIFICATION, "Shutdown requested before classification"
                    )
                    raise asyncio.CancelledError("Shutdown requested")

                await _add_processing_log(db, document, _create_log_entry(
                    "classification", "started",
                    "AI is analyzing document structure and content..."
                ))

                classification = await llm.classify_document(document.raw_text)

                # Log the AI's reasoning (Chain of Thought)
                await _add_processing_log(db, document, _create_log_entry(
                    "classification", "thinking",
                    f"AI Reasoning: {classification.reasoning}",
                    {
                        "classification": classification.classification,
                        "confidence": classification.confidence,
                        "has_experiences": classification.has_experiences,
                        "has_projects": classification.has_projects,
                        "detected_entities": {
                            "companies": classification.detected_entities.companies[:5],
                            "job_titles": classification.detected_entities.job_titles[:5],
                            "skills": classification.detected_entities.skills[:10],
                            "dates": classification.detected_entities.dates[:5],
                        }
                    }
                ))

                document.document_class = DocumentClass(classification.classification)
                document.classification_confidence = classification.confidence
                document.classification_reasoning = classification.reasoning
                await db.commit()

                await _add_processing_log(db, document, _create_log_entry(
                    "classification", "completed",
                    f"Classified as: {classification.classification.upper()} (confidence: {classification.confidence:.0%})"
                ))

                # Cache classification result in checkpoint for resume
                classification_cache = {
                    "classification": classification.classification,
                    "confidence": classification.confidence,
                    "reasoning": classification.reasoning,
                    "has_experiences": classification.has_experiences,
                    "has_projects": classification.has_projects,
                    "detected_entities": {
                        "companies": classification.detected_entities.companies,
                        "job_titles": classification.detected_entities.job_titles,
                        "skills": classification.detected_entities.skills,
                        "dates": classification.detected_entities.dates,
                    }
                }
                await checkpoint_manager.save_checkpoint(
                    ProcessingStep.CLASSIFICATION,
                    extra_data={"classification_result": classification_cache}
                )
                logger.debug(f"Checkpoint saved: CLASSIFICATION for document {document_id}")

            else:
                # Restore classification from checkpoint
                classification = restore_classification_from_checkpoint(
                    checkpoint_manager.state.classification_result
                )
                logger.info(f"Restored classification from checkpoint for document {document_id}")

            # Determine what to extract based on classification
            should_extract_experiences = (
                classification.classification == "resume" or
                classification.classification == "experience" or
                classification.has_experiences
            )
            should_extract_projects = (
                classification.classification == "resume" or
                classification.classification == "project" or
                classification.has_projects
            )
            should_extract_skills = True
            should_extract_publications = True

            # Check if agent pipeline is enabled
            settings = get_settings()
            use_agents = settings.use_agent_pipeline

            if use_agents:
                # ========== AGENT PIPELINE: Multi-Agent Extraction ==========
                # Uses Supervisor to orchestrate specialized agents with validation and refinement
                await _add_processing_log(db, document, _create_log_entry(
                    "agent_pipeline", "started",
                    "Starting multi-agent extraction pipeline with validation..."
                ))

                from src.agents import create_supervisor

                # Check for shutdown before agent pipeline
                if is_shutdown_requested() or checkpoint_manager.shutdown_requested:
                    await checkpoint_manager.save_interrupt_state(
                        ProcessingStep.EXPERIENCE_EXTRACTION,
                        "Shutdown requested before agent pipeline"
                    )
                    raise asyncio.CancelledError("Shutdown requested")

                supervisor = create_supervisor(llm)
                supervisor_result = await supervisor.process(
                    document_id=document_id,
                    user_id=user_id,
                    document_text=document.raw_text,
                    classification=classification,
                    max_refinements=settings.agent_max_refinements,
                )

                # Log agent pipeline results
                await _add_processing_log(db, document, _create_log_entry(
                    "agent_pipeline", "thinking",
                    f"Agents run: {', '.join(supervisor_result.agents_run)}",
                    {
                        "agents_run": supervisor_result.agents_run,
                        "tool_calls": len(supervisor_result.tool_calls_made),
                        "refinements": supervisor_result.total_refinements,
                        "errors": supervisor_result.errors,
                    }
                ))

                # Store results from Supervisor
                extraction_counts = await _store_supervisor_results(
                    db, embedding_service, vector_store, document, user_id, supervisor_result
                )

                await _add_processing_log(db, document, _create_log_entry(
                    "agent_pipeline", "completed",
                    f"Agent pipeline complete: {extraction_counts['experiences']} experiences, "
                    f"{extraction_counts['projects']} projects, {extraction_counts['skills']} skills, "
                    f"{extraction_counts['publications']} publications",
                    {
                        "experiences": extraction_counts["experiences"],
                        "projects": extraction_counts["projects"],
                        "skills": extraction_counts["skills"],
                        "publications": extraction_counts["publications"],
                    }
                ))

                # Save checkpoint after agent pipeline (covers steps 3-6)
                # NOTE: Supervisor extracts publications too, so we save at PUBLICATION_EXTRACTION
                await checkpoint_manager.save_checkpoint(
                    ProcessingStep.PUBLICATION_EXTRACTION,
                    extra_data={"extraction_counts": extraction_counts}
                )
                logger.info(
                    f"Agent pipeline complete for document {document_id}: "
                    f"{extraction_counts['experiences']} experiences, "
                    f"{extraction_counts['projects']} projects, "
                    f"{extraction_counts['skills']} skills, "
                    f"{extraction_counts['publications']} publications"
                )

                # Note: Supervisor extracts everything including skills and publications

            else:
                # ========== LEGACY PIPELINE: Direct LLM Extraction ==========
                # Uses individual extraction calls without agent refinement

                # ========== Step 3: Experience Extraction ==========
                if not checkpoint_manager.state.is_step_completed(ProcessingStep.EXPERIENCE_EXTRACTION):
                    # Check for shutdown
                    if is_shutdown_requested() or checkpoint_manager.shutdown_requested:
                        await checkpoint_manager.save_interrupt_state(
                            ProcessingStep.EXPERIENCE_EXTRACTION, "Shutdown requested before experience extraction"
                        )
                        raise asyncio.CancelledError("Shutdown requested")

                    if should_extract_experiences:
                        await _add_processing_log(db, document, _create_log_entry(
                            "experience_extraction", "started",
                            "AI is extracting work experiences..."
                        ))

                        extraction_result = await _extract_experiences(
                            db, llm, embedding_service, vector_store, document, user_id
                        )
                        extraction_counts["experiences"] = extraction_result.get("count", 0)
                        vectors_stored = extraction_result.get("vectors_stored", 0)

                        details = {"experiences": extraction_result.get("summary", [])}
                        if vectors_stored > 0:
                            details["vectors_stored"] = vectors_stored

                        await _add_processing_log(db, document, _create_log_entry(
                            "experience_extraction", "completed",
                            f"Extracted {extraction_counts['experiences']} work experience(s)",
                            details
                        ))

                    await checkpoint_manager.save_checkpoint(
                        ProcessingStep.EXPERIENCE_EXTRACTION,
                        extra_data={"extraction_counts": extraction_counts}
                    )
                    logger.debug(f"Checkpoint saved: EXPERIENCE_EXTRACTION for document {document_id}")

                # ========== Step 4: Project Extraction ==========
                if not checkpoint_manager.state.is_step_completed(ProcessingStep.PROJECT_EXTRACTION):
                    # Check for shutdown
                    if is_shutdown_requested() or checkpoint_manager.shutdown_requested:
                        await checkpoint_manager.save_interrupt_state(
                            ProcessingStep.PROJECT_EXTRACTION, "Shutdown requested before project extraction"
                        )
                        raise asyncio.CancelledError("Shutdown requested")

                    if should_extract_projects:
                        await _add_processing_log(db, document, _create_log_entry(
                            "project_extraction", "started",
                            "AI is extracting projects..."
                        ))

                        extraction_result = await _extract_projects(
                            db, llm, embedding_service, vector_store, document, user_id
                        )
                        extraction_counts["projects"] = extraction_result.get("count", 0)

                        enrichment_count = extraction_result.get("enrichment_queued", 0)
                        vectors_stored = extraction_result.get("vectors_stored", 0)
                        message = f"Extracted {extraction_counts['projects']} project(s)"
                        if enrichment_count > 0:
                            message += f" ({enrichment_count} queued for GitHub enrichment)"

                        details = {
                            "projects": extraction_result.get("summary", []),
                            "enrichment_queued": enrichment_count,
                        }
                        if vectors_stored > 0:
                            details["vectors_stored"] = vectors_stored

                        await _add_processing_log(db, document, _create_log_entry(
                            "project_extraction", "completed",
                            message,
                            details
                        ))

                    await checkpoint_manager.save_checkpoint(
                        ProcessingStep.PROJECT_EXTRACTION,
                        extra_data={"extraction_counts": extraction_counts}
                    )
                    logger.debug(f"Checkpoint saved: PROJECT_EXTRACTION for document {document_id}")

                # ========== Step 5: Skill Extraction ==========
                if not checkpoint_manager.state.is_step_completed(ProcessingStep.SKILL_EXTRACTION):
                    # Check for shutdown
                    if is_shutdown_requested() or checkpoint_manager.shutdown_requested:
                        await checkpoint_manager.save_interrupt_state(
                            ProcessingStep.SKILL_EXTRACTION, "Shutdown requested before skill extraction"
                        )
                        raise asyncio.CancelledError("Shutdown requested")

                    if should_extract_skills:
                        await _add_processing_log(db, document, _create_log_entry(
                            "skill_extraction", "started",
                            "AI is extracting skills..."
                        ))

                        extraction_result = await _extract_skills(
                            db, llm, document, user_id
                        )
                        extraction_counts["skills"] = extraction_result.get("count", 0)

                        await _add_processing_log(db, document, _create_log_entry(
                            "skill_extraction", "completed",
                            f"Extracted {extraction_counts['skills']} skill(s)",
                            {"skills": extraction_result.get("summary", [])}
                        ))

                    await checkpoint_manager.save_checkpoint(
                        ProcessingStep.SKILL_EXTRACTION,
                        extra_data={"extraction_counts": extraction_counts}
                    )
                    logger.debug(f"Checkpoint saved: SKILL_EXTRACTION for document {document_id}")

            # ========== Step 6: Publication Extraction ==========
            if not checkpoint_manager.state.is_step_completed(ProcessingStep.PUBLICATION_EXTRACTION):
                # Check for shutdown
                if is_shutdown_requested() or checkpoint_manager.shutdown_requested:
                    await checkpoint_manager.save_interrupt_state(
                        ProcessingStep.PUBLICATION_EXTRACTION, "Shutdown requested before publication extraction"
                    )
                    raise asyncio.CancelledError("Shutdown requested")

                if should_extract_publications:
                    await _add_processing_log(db, document, _create_log_entry(
                        "publication_extraction", "started",
                        "AI is extracting publications..."
                    ))

                    extraction_result = await _extract_publications(
                        db, llm, document, user_id
                    )
                    extraction_counts["publications"] = extraction_result.get("count", 0)

                    await _add_processing_log(db, document, _create_log_entry(
                        "publication_extraction", "completed",
                        f"Extracted {extraction_counts['publications']} publication(s)",
                        {"publications": extraction_result.get("summary", [])}
                    ))

                await checkpoint_manager.save_checkpoint(
                    ProcessingStep.PUBLICATION_EXTRACTION,
                    extra_data={"extraction_counts": extraction_counts}
                )
                logger.debug(f"Checkpoint saved: PUBLICATION_EXTRACTION for document {document_id}")

            # ========== Complete ==========
            # Mark as completed and clear checkpoint
            document.processing_status = TaskStatus.COMPLETED
            await db.commit()
            await checkpoint_manager.clear_checkpoint()

            await _add_processing_log(db, document, _create_log_entry(
                "complete", "success",
                f"Processing complete! Found {extraction_counts['experiences']} experiences, "
                f"{extraction_counts['projects']} projects, {extraction_counts['skills']} skills, "
                f"{extraction_counts['publications']} publications.",
                {
                    "classification": classification.classification,
                    "experiences_extracted": extraction_counts["experiences"],
                    "projects_extracted": extraction_counts["projects"],
                    "skills_extracted": extraction_counts["skills"],
                    "publications_extracted": extraction_counts["publications"],
                }
            ))

            # Publish done event for SSE
            try:
                await publish_done(
                    document_id=document_id,
                    result={
                        "classification": classification.classification,
                        "confidence": classification.confidence,
                        "experiences": extraction_counts["experiences"],
                        "projects": extraction_counts["projects"],
                        "skills": extraction_counts["skills"],
                        "publications": extraction_counts["publications"],
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to publish done event: {e}")

            logger.info(
                f"Document {document_id} processed successfully: "
                f"{classification.classification} (confidence: {classification.confidence:.2f}), "
                f"{extraction_counts['experiences']} experiences, {extraction_counts['projects']} projects, "
                f"{extraction_counts['skills']} skills, {extraction_counts['publications']} publications"
            )

            return {
                "status": "success",
                "classification": classification.classification,
                "confidence": classification.confidence,
                "experiences": extraction_counts["experiences"],
                "projects": extraction_counts["projects"],
            }

        except asyncio.CancelledError:
            # Graceful shutdown - state already saved in interrupt handler
            logger.info(f"Document {document_id} processing interrupted by shutdown")
            return {"status": "interrupted", "message": "Processing interrupted by shutdown"}

        except Exception as e:
            logger.exception(f"Error processing document {document_id}: {e}")

            # Save error state to checkpoint if manager is available
            current_step_name = None
            if checkpoint_manager:
                try:
                    current_step = checkpoint_manager.get_resume_step()
                    current_step_name = current_step.value
                    await checkpoint_manager.save_interrupt_state(current_step, str(e))
                except Exception as save_error:
                    logger.warning(f"Failed to save error checkpoint: {save_error}")

            # Add error log
            await _add_processing_log(db, document, _create_log_entry(
                "error", "failed",
                f"Processing failed: {str(e)}"
            ))

            # Publish error event for SSE
            try:
                await publish_error(
                    document_id=document_id,
                    error=str(e),
                    step=current_step_name,
                )
            except Exception as pub_error:
                logger.warning(f"Failed to publish error event: {pub_error}")

            # Update document status
            document.processing_status = TaskStatus.FAILED
            document.processing_error = str(e)
            await db.commit()

            return {"status": "error", "message": str(e)}

        finally:
            # Always unregister checkpoint manager
            if checkpoint_manager:
                unregister_checkpoint_manager(document_id)


async def _extract_text(document: Document) -> str:
    """Extract text from document based on source type.

    Args:
        document: Document model instance.

    Returns:
        Extracted text content.
    """
    from src.parsers.pdf_parser import PDFParser
    from src.parsers.docx_parser import DocxParser

    if not document.file_path:
        return ""

    mime_type = document.mime_type or ""

    if "pdf" in mime_type:
        return PDFParser.parse(document.file_path)
    elif "wordprocessingml" in mime_type or "docx" in mime_type:
        return DocxParser.parse(document.file_path)
    else:
        # Try to read as plain text
        try:
            with open(document.file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""


def _is_likely_project_not_experience(company: str, role: str) -> bool:
    """Check if an extracted 'experience' is likely a project misclassified as employment.

    Args:
        company: The extracted company name.
        role: The extracted role/title.

    Returns:
        True if this looks like a project, not real employment.
    """
    company_lower = company.lower().strip()
    role_lower = role.lower().strip()

    # Project-like company names (not real companies)
    project_patterns = [
        "personal project",
        "side project",
        "hobby project",
        "academic project",
        "course project",
        "portfolio",
        "freelance",
        "self-employed",
        "independent",
        "open source",
        "github",
        "n/a",
        "none",
        "-",
        "project",
    ]

    # Check if company name looks like a project
    for pattern in project_patterns:
        if pattern in company_lower:
            return True

    # Check if company name is too descriptive (likely a project name)
    descriptive_words = ["platform", "application", "system", "tool", "website", "app", "bot", "dashboard"]
    words = company_lower.split()
    if len(words) >= 2:
        for word in descriptive_words:
            if word in company_lower and not any(suffix in company_lower for suffix in ["inc", "llc", "ltd", "corp", "co.", "company"]):
                return True

    # Check if role looks project-like rather than employment
    project_roles = ["creator", "maintainer", "contributor", "author", "builder"]
    for proj_role in project_roles:
        if proj_role in role_lower and "lead" not in role_lower:
            return True

    return False


async def _extract_experiences(
    db,
    llm,
    embedding_service,
    vector_store,
    document: Document,
    user_id: UUID,
) -> dict:
    """Extract and store experiences from document.

    Args:
        db: Database session.
        llm: LLM client.
        embedding_service: Embedding service.
        vector_store: VectorStore instance (may be None if ChromaDB unavailable).
        document: Source document.
        user_id: Owner user ID.

    Returns:
        dict with count, summary, and vectors_stored count.
    """
    extraction = await llm.extract_experiences(document.raw_text)
    summary = []
    skipped_count = 0
    bullets_for_vector_store = []

    for exp_data in extraction.experiences:
        # Post-extraction validation: skip entries that look like projects
        if _is_likely_project_not_experience(exp_data.company, exp_data.role):
            logger.info(
                f"Skipping project-like entry: {exp_data.company} - {exp_data.role} "
                f"(detected as project, not employment)"
            )
            skipped_count += 1
            continue
        # Parse dates
        start_date = _parse_date(exp_data.start_date)
        end_date = _parse_date(exp_data.end_date) if exp_data.end_date else None

        experience = Experience(
            user_id=user_id,
            source_document_id=document.id,
            company=exp_data.company,
            role=exp_data.role,
            location=exp_data.location,
            start_date=start_date,
            end_date=end_date,
            is_current=exp_data.is_current,
        )
        db.add(experience)
        await db.flush()

        # Add to summary for COT logging
        summary.append({
            "company": exp_data.company,
            "role": exp_data.role,
            "bullets_count": len(exp_data.bullets),
        })

        # Add bullets with embeddings
        for idx, bullet_data in enumerate(exp_data.bullets):
            # Generate embedding
            embedding = await embedding_service.embed_single(bullet_data.content)
            embedding_id = f"exp_bullet_{experience.id}_{idx}"

            bullet = ExperienceBullet(
                experience_id=experience.id,
                content=bullet_data.content,
                order_index=idx,
                skills=bullet_data.skills,
                metrics=bullet_data.metrics,
                action_verbs=bullet_data.action_verbs,
                embedding_id=embedding_id,
            )
            db.add(bullet)
            await db.flush()  # Get bullet.id

            # Collect for batch storage in ChromaDB
            bullets_for_vector_store.append({
                "embedding_id": embedding_id,
                "embedding": embedding,
                "content": bullet_data.content,
                "user_id": user_id,
                "bullet_id": bullet.id,
                "document_id": document.id,
                "bullet_type": "experience",
            })

        await db.commit()

    # Batch store all experience bullets in ChromaDB
    vectors_stored = await _store_bullets_batch_in_vector_store(
        vector_store, bullets_for_vector_store
    )

    actual_count = len(extraction.experiences) - skipped_count
    logger.info(
        f"Extracted {actual_count} experiences from document {document.id} "
        f"(skipped {skipped_count} project-like entries, {vectors_stored} vectors stored)"
    )

    return {
        "count": actual_count,
        "summary": summary,
        "skipped_as_projects": skipped_count,
        "vectors_stored": vectors_stored,
    }


async def _extract_projects(
    db,
    llm,
    embedding_service,
    vector_store,
    document: Document,
    user_id: UUID,
) -> dict:
    """Extract and store projects from document.

    Args:
        db: Database session.
        llm: LLM client.
        embedding_service: Embedding service.
        vector_store: VectorStore instance (may be None if ChromaDB unavailable).
        document: Source document.
        user_id: Owner user ID.

    Returns:
        dict with count, summary, and vectors_stored count.
    """
    extraction = await llm.extract_projects(document.raw_text)
    summary = []
    projects_to_enrich = []  # Track projects with GitHub links for auto-enrichment
    bullets_for_vector_store = []

    for proj_data in extraction.projects:
        start_date = _parse_date(proj_data.start_date) if proj_data.start_date else None
        end_date = _parse_date(proj_data.end_date) if proj_data.end_date else None

        project = Project(
            user_id=user_id,
            source_document_id=document.id,
            name=proj_data.name,
            description=proj_data.description,
            technologies=proj_data.technologies,
            start_date=start_date,
            end_date=end_date,
        )
        db.add(project)
        await db.flush()

        # Add to summary for COT logging
        summary.append({
            "name": proj_data.name,
            "technologies": proj_data.technologies[:5] if proj_data.technologies else [],
            "bullets_count": len(proj_data.bullets),
        })

        # Add bullets with embeddings
        for idx, bullet_data in enumerate(proj_data.bullets):
            embedding = await embedding_service.embed_single(bullet_data.content)
            embedding_id = f"proj_bullet_{project.id}_{idx}"

            bullet = ProjectBullet(
                project_id=project.id,
                content=bullet_data.content,
                order_index=idx,
                skills=bullet_data.skills,
                metrics=bullet_data.metrics,
                embedding_id=embedding_id,
            )
            db.add(bullet)
            await db.flush()  # Get bullet.id

            # Collect for batch storage in ChromaDB
            bullets_for_vector_store.append({
                "embedding_id": embedding_id,
                "embedding": embedding,
                "content": bullet_data.content,
                "user_id": user_id,
                "bullet_id": bullet.id,
                "document_id": document.id,
                "bullet_type": "project",
            })

        # Add links (only valid URLs) and track GitHub links for enrichment
        github_url = None
        for link_data in proj_data.links:
            url = link_data.get("url", "")
            if not _is_valid_url(url):
                logger.debug(f"Skipping invalid link URL: {url}")
                continue

            link_type = _map_link_type(link_data.get("type", "other"))
            link = ProjectLink(
                project_id=project.id,
                url=url,
                link_type=link_type,
                title=link_data.get("title"),
            )
            db.add(link)

            # Track GitHub URL for auto-enrichment
            if link_type == LinkType.GITHUB and not github_url:
                github_url = url

        await db.commit()

        # Queue for enrichment if GitHub link found
        if github_url:
            projects_to_enrich.append((project.id, github_url))

    # Batch store all project bullets in ChromaDB
    vectors_stored = await _store_bullets_batch_in_vector_store(
        vector_store, bullets_for_vector_store
    )

    # Auto-enrich projects with GitHub links
    if projects_to_enrich:
        await _enqueue_project_enrichments(db, user_id, projects_to_enrich)

    logger.info(
        f"Extracted {len(extraction.projects)} projects from document {document.id} "
        f"({vectors_stored} vectors stored)"
    )

    return {
        "count": len(extraction.projects),
        "summary": summary,
        "enrichment_queued": len(projects_to_enrich),
        "vectors_stored": vectors_stored,
    }


def _parse_date(date_str: str | None) -> date | None:
    """Parse a date string in YYYY-MM format.

    Args:
        date_str: Date string like "2023-06" or "2023-06-15".

    Returns:
        Parsed date or None.
    """
    if not date_str:
        return None

    try:
        parts = date_str.split("-")
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _map_link_type(type_str: str) -> LinkType:
    """Map string link type to enum.

    Args:
        type_str: Link type string.

    Returns:
        LinkType enum value.
    """
    mapping = {
        "github": LinkType.GITHUB,
        "demo": LinkType.DEMO,
        "paper": LinkType.PAPER,
        "docs": LinkType.DOCS,
        "documentation": LinkType.DOCS,
        "video": LinkType.VIDEO,
    }
    return mapping.get(type_str.lower(), LinkType.OTHER)


def _is_valid_url(url: str | None) -> bool:
    """Check if a URL is valid and not localhost.

    Args:
        url: URL to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not url:
        return False

    url = url.strip()

    # Must start with http:// or https://
    if not (url.startswith("http://") or url.startswith("https://")):
        return False

    # Reject localhost and local URLs
    invalid_patterns = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "example.com",
        "placeholder",
        ".local",
    ]
    url_lower = url.lower()
    for pattern in invalid_patterns:
        if pattern in url_lower:
            return False

    # Basic structure check - should have domain
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return bool(parsed.netloc and "." in parsed.netloc)
    except Exception:
        return False


async def _enqueue_project_enrichments(
    db,
    user_id: UUID,
    projects_to_enrich: list[tuple[UUID, str]],
) -> None:
    """Enqueue enrichment tasks for projects with GitHub links.

    Args:
        db: Database session.
        user_id: Owner user ID.
        projects_to_enrich: List of (project_id, github_url) tuples.
    """
    from arq import create_pool
    from src.tasks.worker import get_redis_settings
    from src.integrations.github import GitHubService

    try:
        arq = await create_pool(get_redis_settings())

        for project_id, github_url in projects_to_enrich:
            # Validate GitHub URL before enqueueing
            parsed = GitHubService.parse_github_url(github_url)
            if not parsed:
                logger.warning(f"Invalid GitHub URL for project {project_id}: {github_url}")
                continue

            # Create background task record
            task = BackgroundTask(
                user_id=user_id,
                task_type="enrich_project",
                entity_id=project_id,
                status=TaskStatus.PENDING,
                progress=0,
            )
            db.add(task)
            await db.flush()

            # Enqueue enrichment task
            await arq.enqueue_job(
                "enrich_project_from_github",
                project_id,
                user_id,
                github_url,
            )
            logger.info(f"Auto-enqueued enrichment for project {project_id} from {github_url}")

        await arq.close()
        await db.commit()

    except Exception as e:
        logger.warning(f"Failed to enqueue project enrichments: {e}")
        # Don't fail the document processing - enrichment is a bonus


def _map_skill_category(category_str: str) -> SkillCategory:
    """Map LLM skill category string to database enum.

    Args:
        category_str: Category string from LLM output.

    Returns:
        SkillCategory enum value.
    """
    mapping = {
        "programming_language": SkillCategory.PROGRAMMING_LANGUAGE,
        "framework": SkillCategory.FRAMEWORK,
        "database": SkillCategory.DATABASE,
        "cloud": SkillCategory.CLOUD,
        "devops": SkillCategory.DEVOPS,
        "tool": SkillCategory.TOOL,
        "soft_skill": SkillCategory.SOFT_SKILL,
        "methodology": SkillCategory.METHODOLOGY,
        "other": SkillCategory.OTHER,
    }
    return mapping.get(category_str.lower(), SkillCategory.OTHER)


def _map_proficiency_level(proficiency_str: str | None) -> ProficiencyLevel | None:
    """Map LLM proficiency string to database enum.

    Args:
        proficiency_str: Proficiency string from LLM output.

    Returns:
        ProficiencyLevel enum value or None.
    """
    if not proficiency_str:
        return None

    mapping = {
        "beginner": ProficiencyLevel.BEGINNER,
        "intermediate": ProficiencyLevel.INTERMEDIATE,
        "advanced": ProficiencyLevel.ADVANCED,
        "expert": ProficiencyLevel.EXPERT,
    }
    return mapping.get(proficiency_str.lower())


def _map_publication_type(type_str: str) -> PublicationType:
    """Map LLM publication type string to database enum.

    Args:
        type_str: Publication type string from LLM output.

    Returns:
        PublicationType enum value.
    """
    mapping = {
        "journal": PublicationType.JOURNAL,
        "conference": PublicationType.CONFERENCE,
        "workshop": PublicationType.WORKSHOP,
        "book": PublicationType.BOOK_CHAPTER,
        "book_chapter": PublicationType.BOOK_CHAPTER,
        "thesis": PublicationType.THESIS,
        "patent": PublicationType.PATENT,
        "preprint": PublicationType.PREPRINT,
        "other": PublicationType.OTHER,
    }
    return mapping.get(type_str.lower(), PublicationType.OTHER)


async def _extract_skills(
    db,
    llm,
    document: Document,
    user_id: UUID,
) -> dict:
    """Extract and store skills from document.

    Args:
        db: Database session.
        llm: LLM client.
        document: Source document.
        user_id: Owner user ID.

    Returns:
        dict with count and summary of extracted skills.
    """
    try:
        extraction = await llm.extract_skills(document.raw_text)
        summary = []
        skills_added = 0

        # Get existing skills for this user to avoid duplicates (exclude soft-deleted)
        from sqlalchemy import select
        existing_result = await db.execute(
            select(Skill.name).where(
                Skill.user_id == user_id,
                Skill.deleted_at.is_(None)  # Exclude soft-deleted
            )
        )
        existing_skill_names = {name.lower() for name in existing_result.scalars().all()}

        for skill_data in extraction.skills:
            # Skip if skill already exists for this user
            if skill_data.name.lower() in existing_skill_names:
                logger.debug(f"Skipping duplicate skill: {skill_data.name}")
                continue

            skill = Skill(
                user_id=user_id,
                name=skill_data.name,
                category=_map_skill_category(skill_data.category),
                proficiency=_map_proficiency_level(skill_data.proficiency),
                years_of_experience=skill_data.years_experience,
                display_order=skills_added,
            )
            db.add(skill)
            skills_added += 1
            existing_skill_names.add(skill_data.name.lower())  # Prevent duplicates within batch

            summary.append({
                "name": skill_data.name,
                "category": skill_data.category,
            })

        await db.commit()
        logger.info(f"Extracted {skills_added} skills from document {document.id}")

        return {
            "count": skills_added,
            "summary": summary[:20],  # Limit summary for logging
        }

    except Exception as e:
        logger.error(f"Failed to extract skills from document {document.id}: {e}")
        return {"count": 0, "summary": [], "error": str(e)}


async def _extract_publications(
    db,
    llm,
    document: Document,
    user_id: UUID,
) -> dict:
    """Extract and store publications from document.

    Args:
        db: Database session.
        llm: LLM client.
        document: Source document.
        user_id: Owner user ID.

    Returns:
        dict with count and summary of extracted publications.
    """
    try:
        extraction = await llm.extract_publications(document.raw_text)
        summary = []
        pubs_added = 0

        # Get existing publications for this user to avoid duplicates (by title)
        from sqlalchemy import select
        existing_result = await db.execute(
            select(Publication.title).where(Publication.user_id == user_id)
        )
        existing_titles = {title.lower() for title in existing_result.scalars().all()}

        for pub_data in extraction.publications:
            # Skip if publication already exists for this user
            if pub_data.title.lower() in existing_titles:
                logger.debug(f"Skipping duplicate publication: {pub_data.title}")
                continue

            # Parse publication date
            pub_date = _parse_date(pub_data.publication_date) if pub_data.publication_date else None

            # Join authors list into string
            authors_str = ", ".join(pub_data.authors) if pub_data.authors else ""

            publication = Publication(
                user_id=user_id,
                source_document_id=document.id,
                title=pub_data.title,
                authors=authors_str,
                publication_type=_map_publication_type(pub_data.publication_type),
                venue=pub_data.venue,
                publication_date=pub_date,
                doi=pub_data.doi,
                url=pub_data.url,
                abstract=pub_data.abstract,
                is_first_author=pub_data.is_first_author,
                display_order=pubs_added,
            )
            db.add(publication)
            pubs_added += 1
            existing_titles.add(pub_data.title.lower())  # Prevent duplicates within batch

            summary.append({
                "title": pub_data.title,
                "type": pub_data.publication_type,
                "venue": pub_data.venue,
            })

        await db.commit()
        logger.info(f"Extracted {pubs_added} publications from document {document.id}")

        return {
            "count": pubs_added,
            "summary": summary[:10],  # Limit summary for logging
        }

    except Exception as e:
        logger.error(f"Failed to extract publications from document {document.id}: {e}")
        return {"count": 0, "summary": [], "error": str(e)}
