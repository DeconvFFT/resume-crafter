"""Background tasks for resume matching."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.database import (
    Experience,
    ExperienceBullet,
    JobDescription,
    JobRequirement,
    Project,
    ProjectBullet,
    ResumeMatch,
    ResumeMatchItem,
    TaskStatus,
)

logger = logging.getLogger(__name__)


async def _search_bullets_in_vector_store(
    vector_store,
    embedding_service,
    query_text: str,
    user_id: UUID,
    n_results: int = 20,
    bullet_type: str | None = None,
) -> list[dict]:
    """Search for similar bullets using ChromaDB vector store.

    Args:
        vector_store: VectorStore instance (may be None).
        embedding_service: Embedding service for generating query embedding.
        query_text: The text to search for.
        user_id: User ID to filter results.
        n_results: Maximum number of results.
        bullet_type: Optional filter for "experience" or "project".

    Returns:
        List of dicts with keys: embedding_id, content, score, metadata.
        Empty list if vector_store is None or search fails.
    """
    if vector_store is None:
        return []

    try:
        # Generate query embedding
        query_embedding = await embedding_service.embed_single(query_text)

        # Search in ChromaDB
        results = await vector_store.query_by_user(
            query_embedding=query_embedding,
            user_id=str(user_id),
            n_results=n_results,
            bullet_type=bullet_type,
        )

        # Format results
        formatted = []
        for i, embedding_id in enumerate(results.get("ids", [])):
            formatted.append({
                "embedding_id": embedding_id,
                "content": results["documents"][i] if results.get("documents") else None,
                "score": 1.0 - results["distances"][i] if results.get("distances") else 0.0,  # Convert distance to similarity
                "metadata": results["metadatas"][i] if results.get("metadatas") else {},
            })
        return formatted

    except Exception as e:
        logger.warning(f"Vector store search failed, falling back to database: {e}")
        return []


async def generate_match(
    ctx: dict,
    match_id: UUID,
    user_id: UUID,
    max_experience_bullets: int = 10,
    max_project_bullets: int = 6,
) -> dict:
    """Generate resume matches: find best bullets for each job requirement.

    Uses ChromaDB for fast semantic search when available, with fallback to
    database-based search if ChromaDB is unavailable.

    Args:
        ctx: ARQ context with db_session_factory and services.
        match_id: ID of the match to generate.
        user_id: ID of the match owner.
        max_experience_bullets: Max experience bullets to include.
        max_project_bullets: Max project bullets to include.

    Returns:
        Matching result with status and scores.
    """
    db_session_factory = ctx["db_session_factory"]
    embedding_service = ctx["embedding_service"]
    vector_store = ctx.get("vector_store")  # May be None if ChromaDB unavailable

    async with db_session_factory() as db:
        try:
            # Get match with job
            result = await db.execute(
                select(ResumeMatch)
                .options(selectinload(ResumeMatch.job).selectinload(JobDescription.requirements))
                .where(
                    ResumeMatch.id == match_id,
                    ResumeMatch.user_id == user_id,
                )
            )
            match = result.scalar_one_or_none()

            if not match:
                logger.error(f"Match {match_id} not found")
                return {"status": "error", "message": "Match not found"}

            # Update status
            match.processing_status = TaskStatus.PROCESSING
            await db.commit()

            # Build a lookup of bullets from the database
            # This is needed to get bullet IDs and parent info even when using vector search
            bullet_lookup = {}  # embedding_id -> bullet_data
            all_bullets = []  # For fallback when vector store unavailable

            # Get user's experience bullets
            exp_result = await db.execute(
                select(Experience)
                .options(selectinload(Experience.bullets))
                .where(
                    Experience.user_id == user_id,
                    Experience.deleted_at.is_(None),
                )
            )
            experiences = exp_result.scalars().all()

            for exp in experiences:
                for bullet in exp.bullets:
                    bullet_data = {
                        "id": str(bullet.id),
                        "content": bullet.content,
                        "source": "experience",
                        "experience_bullet_id": bullet.id,
                        "project_bullet_id": None,
                        "parent": f"{exp.company} - {exp.role}",
                        "embedding_id": bullet.embedding_id,
                    }
                    all_bullets.append(bullet_data)
                    if bullet.embedding_id:
                        bullet_lookup[bullet.embedding_id] = bullet_data

            # Get user's project bullets
            proj_result = await db.execute(
                select(Project)
                .options(selectinload(Project.bullets))
                .where(
                    Project.user_id == user_id,
                    Project.deleted_at.is_(None),
                )
            )
            projects = proj_result.scalars().all()

            for proj in projects:
                for bullet in proj.bullets:
                    bullet_data = {
                        "id": str(bullet.id),
                        "content": bullet.content,
                        "source": "project",
                        "experience_bullet_id": None,
                        "project_bullet_id": bullet.id,
                        "parent": proj.name,
                        "embedding_id": bullet.embedding_id,
                    }
                    all_bullets.append(bullet_data)
                    if bullet.embedding_id:
                        bullet_lookup[bullet.embedding_id] = bullet_data

            if not all_bullets:
                match.processing_status = TaskStatus.COMPLETED
                match.overall_match_score = 0.0
                match.skill_coverage = 0.0
                match.experience_relevance = 0.0
                await db.commit()
                return {"status": "success", "message": "No bullets to match"}

            # Determine search strategy
            use_vector_store = vector_store is not None and len(bullet_lookup) > 0
            if not use_vector_store:
                logger.info("Using fallback embedding search (ChromaDB unavailable or no indexed bullets)")
                # Generate embeddings for fallback search
                bullet_texts = [b["content"] for b in all_bullets]
                bullet_embeddings = await embedding_service.embed(bullet_texts)
            else:
                logger.info(f"Using ChromaDB for semantic search ({len(bullet_lookup)} indexed bullets)")
                bullet_embeddings = None  # Not needed when using vector store

            # For each requirement, find best matching bullets
            from src.core.llm_client import get_llm_client
            llm = get_llm_client()

            total_score = 0.0
            matched_requirements = 0
            selected_bullet_ids = set()

            for requirement in match.job.requirements:
                candidates = []

                if use_vector_store:
                    # Use ChromaDB semantic search
                    vector_results = await _search_bullets_in_vector_store(
                        vector_store,
                        embedding_service,
                        requirement.content,
                        user_id,
                        n_results=10,
                    )

                    # Map vector results to bullet data
                    for vr in vector_results:
                        embedding_id = vr["embedding_id"]
                        if embedding_id in bullet_lookup:
                            bullet_data = bullet_lookup[embedding_id]
                            candidates.append({
                                "id": bullet_data["id"],
                                "content": bullet_data["content"],
                                "source": bullet_data["source"],
                                "initial_score": vr["score"],
                                "experience_bullet_id": bullet_data["experience_bullet_id"],
                                "project_bullet_id": bullet_data["project_bullet_id"],
                            })

                if not candidates:
                    # Fallback to in-memory embedding search
                    if bullet_embeddings is None:
                        bullet_texts = [b["content"] for b in all_bullets]
                        bullet_embeddings = await embedding_service.embed(bullet_texts)

                    req_embedding = await embedding_service.embed_single(requirement.content)
                    similar = embedding_service.find_similar(
                        req_embedding,
                        bullet_embeddings,
                        top_k=10,
                        threshold=0.3,
                    )

                    for idx, score in similar:
                        bullet_data = all_bullets[idx]
                        candidates.append({
                            "id": bullet_data["id"],
                            "content": bullet_data["content"],
                            "source": bullet_data["source"],
                            "initial_score": score,
                            "experience_bullet_id": bullet_data["experience_bullet_id"],
                            "project_bullet_id": bullet_data["project_bullet_id"],
                        })

                if not candidates:
                    continue

                # LLM re-ranking
                try:
                    ranking = await llm.rank_matches(requirement.content, candidates)

                    # Use LLM rankings
                    for ranked in ranking.ranked_bullets[:3]:  # Top 3 per requirement
                        bullet_id = ranked.get("bullet_id")
                        if bullet_id and bullet_id not in selected_bullet_ids:
                            candidate = next(
                                (c for c in candidates if c["id"] == bullet_id), None
                            )
                            if candidate:
                                match_item = ResumeMatchItem(
                                    match_id=match.id,
                                    requirement_id=requirement.id,
                                    experience_bullet_id=candidate["experience_bullet_id"],
                                    project_bullet_id=candidate["project_bullet_id"],
                                    relevance_score=ranked.get("score", 0.5),
                                    match_explanation=ranked.get("explanation", ""),
                                    included_in_resume=True,
                                )
                                db.add(match_item)
                                selected_bullet_ids.add(bullet_id)
                                total_score += ranked.get("score", 0.5)
                                matched_requirements += 1
                                break  # One bullet per requirement
                except Exception as e:
                    logger.warning(f"LLM ranking failed, using semantic similarity scores: {e}")

                    # Fall back to semantic similarity
                    for candidate in candidates[:1]:
                        if candidate["id"] not in selected_bullet_ids:
                            match_item = ResumeMatchItem(
                                match_id=match.id,
                                requirement_id=requirement.id,
                                experience_bullet_id=candidate["experience_bullet_id"],
                                project_bullet_id=candidate["project_bullet_id"],
                                relevance_score=candidate["initial_score"],
                                match_explanation="Matched by semantic similarity",
                                included_in_resume=True,
                            )
                            db.add(match_item)
                            selected_bullet_ids.add(candidate["id"])
                            total_score += candidate["initial_score"]
                            matched_requirements += 1
                            break

            # Calculate overall scores
            num_requirements = len(match.job.requirements)
            match.skill_coverage = matched_requirements / num_requirements if num_requirements > 0 else 0.0
            match.experience_relevance = total_score / matched_requirements if matched_requirements > 0 else 0.0
            match.overall_match_score = (match.skill_coverage + match.experience_relevance) / 2

            match.processing_status = TaskStatus.COMPLETED
            await db.commit()

            search_method = "ChromaDB" if use_vector_store else "in-memory"
            logger.info(
                f"Match {match_id} generated ({search_method}): score={match.overall_match_score:.2f}, "
                f"coverage={match.skill_coverage:.2f}, {matched_requirements} matches"
            )

            return {
                "status": "success",
                "overall_score": match.overall_match_score,
                "skill_coverage": match.skill_coverage,
                "experience_relevance": match.experience_relevance,
                "matched_count": matched_requirements,
                "search_method": search_method,
            }

        except Exception as e:
            logger.exception(f"Error generating match {match_id}: {e}")

            match.processing_status = TaskStatus.FAILED
            await db.commit()

            return {"status": "error", "message": str(e)}
