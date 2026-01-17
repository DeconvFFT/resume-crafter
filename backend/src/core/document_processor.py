"""Document processing orchestrator."""

import logging
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from arq import ArqRedis

from src.models.database import Document, SourceType, TaskStatus, BackgroundTask

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Orchestrates document processing workflow."""

    def __init__(self, arq_redis: ArqRedis):
        """Initialize processor with ARQ connection.

        Args:
            arq_redis: ARQ Redis connection for enqueuing tasks.
        """
        self._arq = arq_redis

    async def process_upload(
        self,
        db,
        user_id: UUID,
        filename: str,
        file_content: BinaryIO,
        mime_type: str,
        file_storage_path: Path,
    ) -> Document:
        """Process an uploaded document.

        Args:
            db: Database session.
            user_id: Owner user ID.
            filename: Original filename.
            file_content: File content as binary stream.
            mime_type: MIME type of the file.
            file_storage_path: Path where file is stored.

        Returns:
            Created Document instance.
        """
        # Create document record
        document = Document(
            user_id=user_id,
            filename=filename,
            file_path=str(file_storage_path),
            mime_type=mime_type,
            source_type=SourceType.LOCAL_FILE,
            processing_status=TaskStatus.PENDING,
        )
        db.add(document)
        await db.flush()
        await db.refresh(document)

        # Create background task record for tracking
        task = BackgroundTask(
            user_id=user_id,
            task_type="process_document",
            entity_id=document.id,
            status=TaskStatus.PENDING,
            progress=0,
        )
        db.add(task)
        await db.flush()

        # Enqueue processing task
        await self._arq.enqueue_job(
            "process_document",
            document.id,
            user_id,
        )

        logger.info(f"Enqueued document processing for {document.id}")
        return document

    async def process_google_doc(
        self,
        db,
        user_id: UUID,
        google_doc_id: str,
    ) -> Document:
        """Process a Google Doc import.

        Args:
            db: Database session.
            user_id: Owner user ID.
            google_doc_id: Google Doc ID.

        Returns:
            Created Document instance.
        """
        document = Document(
            user_id=user_id,
            filename=f"gdoc_{google_doc_id}",
            source_type=SourceType.GOOGLE_DOC,
            source_url=f"https://docs.google.com/document/d/{google_doc_id}",
            processing_status=TaskStatus.PENDING,
        )
        db.add(document)
        await db.flush()
        await db.refresh(document)

        # Create background task record
        task = BackgroundTask(
            user_id=user_id,
            task_type="process_document",
            entity_id=document.id,
            status=TaskStatus.PENDING,
            progress=0,
        )
        db.add(task)
        await db.flush()

        # Enqueue processing task
        await self._arq.enqueue_job(
            "process_document",
            document.id,
            user_id,
        )

        logger.info(f"Enqueued Google Doc processing for {document.id}")
        return document


class JobAnalyzer:
    """Orchestrates job description analysis workflow."""

    def __init__(self, arq_redis: ArqRedis):
        """Initialize analyzer with ARQ connection.

        Args:
            arq_redis: ARQ Redis connection for enqueuing tasks.
        """
        self._arq = arq_redis

    async def analyze_job(
        self,
        db,
        user_id: UUID,
        job_id: UUID,
    ) -> None:
        """Enqueue job analysis task.

        Args:
            db: Database session.
            user_id: Owner user ID.
            job_id: Job description ID.
        """
        # Create background task record
        task = BackgroundTask(
            user_id=user_id,
            task_type="analyze_job",
            entity_id=job_id,
            status=TaskStatus.PENDING,
            progress=0,
        )
        db.add(task)
        await db.flush()

        # Enqueue analysis task
        await self._arq.enqueue_job(
            "analyze_job",
            job_id,
            user_id,
        )

        logger.info(f"Enqueued job analysis for {job_id}")


class MatchGenerator:
    """Orchestrates resume matching workflow."""

    def __init__(self, arq_redis: ArqRedis):
        """Initialize generator with ARQ connection.

        Args:
            arq_redis: ARQ Redis connection for enqueuing tasks.
        """
        self._arq = arq_redis

    async def generate_match(
        self,
        db,
        user_id: UUID,
        match_id: UUID,
        max_experience_bullets: int = 10,
        max_project_bullets: int = 6,
    ) -> None:
        """Enqueue match generation task.

        Args:
            db: Database session.
            user_id: Owner user ID.
            match_id: Resume match ID.
            max_experience_bullets: Max experience bullets to include.
            max_project_bullets: Max project bullets to include.
        """
        # Create background task record
        task = BackgroundTask(
            user_id=user_id,
            task_type="generate_match",
            entity_id=match_id,
            status=TaskStatus.PENDING,
            progress=0,
        )
        db.add(task)
        await db.flush()

        # Enqueue matching task
        await self._arq.enqueue_job(
            "generate_match",
            match_id,
            user_id,
            max_experience_bullets,
            max_project_bullets,
        )

        logger.info(f"Enqueued match generation for {match_id}")
