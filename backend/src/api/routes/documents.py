"""Document routes."""

from typing import Annotated
from uuid import UUID

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import CurrentUser
from src.config import get_settings
from src.models.database import BackgroundTask, Document, SourceType, TaskStatus
from src.models.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentVerifyRequest,
    GoogleDocImportRequest,
)
from src.storage.database import get_db
from src.storage.file_storage import get_file_storage

router = APIRouter()
settings = get_settings()


async def get_arq_redis() -> ArqRedis:
    """Get ARQ Redis connection."""
    from arq import create_pool
    from src.tasks.worker import get_redis_settings
    return await create_pool(get_redis_settings())


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    hint_document_class: str | None = None,
) -> Document:
    """Upload a document file for processing."""
    # Validate file size
    content = await file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB",
        )

    # Validate file type
    if file.content_type not in settings.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type {file.content_type} not allowed",
        )

    # Save file to storage
    file_storage = get_file_storage()
    file_path, file_size = await file_storage.save_bytes(
        user_id=current_user.id,
        content=content,
        original_filename=file.filename or "unnamed",
    )

    # Create document record
    document = Document(
        user_id=current_user.id,
        filename=file.filename or "unnamed",
        file_path=str(file_path),
        file_size_bytes=file_size,
        mime_type=file.content_type,
        source_type=SourceType.LOCAL_FILE,
        processing_status=TaskStatus.PENDING,
    )
    db.add(document)
    await db.flush()

    # Create background task record
    task = BackgroundTask(
        user_id=current_user.id,
        task_type="process_document",
        entity_id=document.id,
        status=TaskStatus.PENDING,
        progress=0,
    )
    db.add(task)
    await db.flush()

    # Enqueue processing task
    try:
        arq = await get_arq_redis()
        await arq.enqueue_job("process_document", document.id, current_user.id)
        await arq.close()
    except Exception as e:
        # Log but don't fail - task can be retried
        import logging
        logging.warning(f"Failed to enqueue document processing: {e}")

    await db.refresh(document)
    return document


@router.post("/google", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def import_google_doc(
    request: GoogleDocImportRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    """Import a Google Doc for processing."""
    from src.integrations.google_docs import GoogleDocsService

    # Extract doc ID from URL if needed
    google_docs = GoogleDocsService()
    try:
        # Fetch the document content (includes PDF for hyperlink extraction)
        doc_content = await google_docs.fetch_document(request.google_doc_id)

        # Save content to file storage
        # IMPORTANT: Save as PDF when available to preserve hyperlinks
        file_storage = get_file_storage()
        if doc_content.pdf_bytes:
            # Save as PDF - this preserves hyperlinks for extraction
            file_path, file_size = await file_storage.save_bytes(
                user_id=current_user.id,
                content=doc_content.pdf_bytes,
                original_filename=f"{doc_content.title}.pdf",
            )
            mime_type = "application/pdf"
        else:
            # Fallback to text if PDF export failed
            file_path, file_size = await file_storage.save_bytes(
                user_id=current_user.id,
                content=doc_content.text.encode("utf-8"),
                original_filename=f"{doc_content.title}.txt",
            )
            mime_type = "text/plain"

        # Create document record
        document = Document(
            user_id=current_user.id,
            filename=doc_content.title,
            file_path=str(file_path),
            file_size_bytes=file_size,
            mime_type=mime_type,
            source_type=SourceType.GOOGLE_DOC,
            source_url=f"https://docs.google.com/document/d/{doc_content.doc_id}",
            processing_status=TaskStatus.PENDING,
        )
        db.add(document)
        await db.flush()

        # Create background task record
        task = BackgroundTask(
            user_id=current_user.id,
            task_type="process_document",
            entity_id=document.id,
            status=TaskStatus.PENDING,
            progress=0,
        )
        db.add(task)
        await db.flush()

        # Enqueue processing task
        try:
            arq = await get_arq_redis()
            await arq.enqueue_job("process_document", document.id, current_user.id)
            await arq.close()
        except Exception as e:
            import logging
            logging.warning(f"Failed to enqueue document processing: {e}")

        await db.refresh(document)
        return document

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch Google Doc: {str(e)}",
        )
    finally:
        await google_docs.close()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentListResponse:
    """List all documents for current user."""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id, Document.deleted_at.is_(None))
        .order_by(Document.created_at.desc())
    )
    documents = result.scalars().all()

    return DocumentListResponse(items=list(documents), total=len(documents))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    """Get a specific document."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return document


@router.put("/{document_id}/verify", response_model=DocumentResponse)
async def verify_document(
    document_id: UUID,
    request: DocumentVerifyRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    """Verify or correct document classification."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    from src.models.database import DocumentClass
    document.document_class = DocumentClass(request.document_class)
    document.verified_by_user = True

    await db.flush()
    await db.refresh(document)

    return document


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Document:
    """Reprocess a document with the latest extraction logic.

    This clears the document's extracted data and re-queues it for processing.
    Use this after updating extraction prompts or fixing bugs.
    """
    from datetime import datetime, timezone
    from src.models.database import Experience, Project, Skill, Publication

    # Get the document
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Soft delete existing extracted data for this document
    now = datetime.now(timezone.utc)

    # Delete experiences from this document
    await db.execute(
        Experience.__table__.update()
        .where(Experience.source_document_id == document_id)
        .values(deleted_at=now)
    )

    # Delete projects from this document
    await db.execute(
        Project.__table__.update()
        .where(Project.source_document_id == document_id)
        .values(deleted_at=now)
    )

    # Delete skills (they don't have source_document_id, but we can clear all for user)
    # We don't delete skills as they may come from multiple documents

    # Delete publications from this document
    await db.execute(
        Publication.__table__.update()
        .where(Publication.source_document_id == document_id)
        .values(deleted_at=now)
    )

    # Reset document processing state
    document.processing_status = TaskStatus.PENDING
    document.processing_logs = []
    document.checkpoint_state = None
    document.checkpoint_step = None
    document.checkpoint_timestamp = None
    document.processing_attempt = 0

    await db.flush()

    # Create new background task
    task = BackgroundTask(
        user_id=current_user.id,
        task_type="process_document",
        entity_id=document.id,
        status=TaskStatus.PENDING,
        progress=0,
    )
    db.add(task)
    await db.flush()

    # Enqueue processing
    try:
        arq = await get_arq_redis()
        await arq.enqueue_job("process_document", document.id, current_user.id)
        await arq.close()
    except Exception as e:
        import logging
        logging.warning(f"Failed to enqueue document reprocessing: {e}")

    await db.refresh(document)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft delete a document."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == current_user.id,
            Document.deleted_at.is_(None),
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    from datetime import datetime, timezone
    document.deleted_at = datetime.now(timezone.utc)

    await db.flush()
