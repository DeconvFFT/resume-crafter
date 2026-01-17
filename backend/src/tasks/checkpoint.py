"""Checkpoint management for resumable document processing.

Provides fault-tolerant document processing by saving checkpoint state
after each pipeline step. If processing is interrupted (SIGTERM, timeout,
error), it can resume from the last successful checkpoint.

Based on patterns from LangGraph checkpointing and the ResumableAgent pattern.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ProcessingStep(str, Enum):
    """Document processing pipeline steps in execution order."""

    TEXT_EXTRACTION = "text_extraction"
    CLASSIFICATION = "classification"
    EXPERIENCE_EXTRACTION = "experience_extraction"
    PROJECT_EXTRACTION = "project_extraction"
    SKILL_EXTRACTION = "skill_extraction"
    PUBLICATION_EXTRACTION = "publication_extraction"
    COMPLETE = "complete"

    @classmethod
    def ordered_steps(cls) -> list["ProcessingStep"]:
        """Return steps in execution order (excluding COMPLETE)."""
        return [
            cls.TEXT_EXTRACTION,
            cls.CLASSIFICATION,
            cls.EXPERIENCE_EXTRACTION,
            cls.PROJECT_EXTRACTION,
            cls.SKILL_EXTRACTION,
            cls.PUBLICATION_EXTRACTION,
        ]

    @classmethod
    def next_step(cls, current: "ProcessingStep") -> "ProcessingStep | None":
        """Get the next step after current, or None if complete."""
        steps = cls.ordered_steps()
        try:
            idx = steps.index(current)
            if idx + 1 < len(steps):
                return steps[idx + 1]
            return cls.COMPLETE
        except ValueError:
            return None


@dataclass
class CheckpointState:
    """Represents the checkpoint state for document processing.

    Stores:
    - completed_steps: List of step names that have finished successfully
    - classification_result: Cached LLM classification result (expensive to recompute)
    - extraction_counts: Number of entities extracted in each step
    - last_error: Error message if processing failed
    - interrupted_at_step: Step name where processing was interrupted
    """

    completed_steps: list[str] = field(default_factory=list)
    classification_result: dict | None = None
    extraction_counts: dict = field(
        default_factory=lambda: {
            "experiences": 0,
            "projects": 0,
            "skills": 0,
            "publications": 0,
        }
    )
    last_error: str | None = None
    interrupted_at_step: str | None = None

    def to_dict(self) -> dict:
        """Serialize state to dictionary for JSONB storage."""
        return {
            "completed_steps": self.completed_steps,
            "classification_result": self.classification_result,
            "extraction_counts": self.extraction_counts,
            "last_error": self.last_error,
            "interrupted_at_step": self.interrupted_at_step,
        }

    @classmethod
    def from_dict(cls, data: dict | None) -> "CheckpointState":
        """Deserialize state from dictionary."""
        if not data:
            return cls()
        return cls(
            completed_steps=data.get("completed_steps", []),
            classification_result=data.get("classification_result"),
            extraction_counts=data.get(
                "extraction_counts",
                {
                    "experiences": 0,
                    "projects": 0,
                    "skills": 0,
                    "publications": 0,
                },
            ),
            last_error=data.get("last_error"),
            interrupted_at_step=data.get("interrupted_at_step"),
        )

    def is_step_completed(self, step: ProcessingStep) -> bool:
        """Check if a step has been completed."""
        return step.value in self.completed_steps

    def mark_step_completed(self, step: ProcessingStep) -> None:
        """Mark a step as completed."""
        if step.value not in self.completed_steps:
            self.completed_steps.append(step.value)
        # Clear any interrupted state when a step completes
        self.interrupted_at_step = None
        self.last_error = None

    def update_extraction_count(self, entity_type: str, count: int) -> None:
        """Update extraction count for an entity type."""
        self.extraction_counts[entity_type] = count


class CheckpointManager:
    """Manages checkpoint state for document processing.

    Usage:
        async with db_session_factory() as db:
            document = await get_document(...)
            manager = CheckpointManager(db, document)

            resume_step = manager.get_resume_step()
            if resume_step != ProcessingStep.TEXT_EXTRACTION:
                logger.info(f"Resuming from {resume_step}")

            for step in ProcessingStep.ordered_steps():
                if manager.state.is_step_completed(step):
                    continue  # Skip completed steps

                if manager.shutdown_requested:
                    await manager.save_interrupt_state(step)
                    raise asyncio.CancelledError("Shutdown requested")

                result = await execute_step(step)
                await manager.save_checkpoint(step, extra_data=result)

            await manager.clear_checkpoint()  # Success!
    """

    def __init__(self, db: AsyncSession, document: Any):
        """Initialize checkpoint manager.

        Args:
            db: Database session for persisting checkpoints.
            document: Document ORM model instance.
        """
        self.db = db
        self.document = document
        self._state: CheckpointState | None = None
        self._shutdown_requested = False

    @property
    def state(self) -> CheckpointState:
        """Get or load checkpoint state from document."""
        if self._state is None:
            self._state = CheckpointState.from_dict(self.document.checkpoint_state)
        return self._state

    def request_shutdown(self) -> None:
        """Signal that graceful shutdown has been requested.

        Called by SIGTERM handler to notify active tasks to save state.
        """
        self._shutdown_requested = True
        logger.info(f"Shutdown requested for document {self.document.id}")

    @property
    def shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self._shutdown_requested

    async def save_checkpoint(
        self,
        step: ProcessingStep,
        completed: bool = True,
        extra_data: dict | None = None,
    ) -> None:
        """Save checkpoint state to database.

        Args:
            step: The processing step being checkpointed.
            completed: Whether the step completed successfully.
            extra_data: Additional data to store (classification_result, extraction_counts).
        """
        if completed:
            self.state.mark_step_completed(step)
        else:
            self.state.interrupted_at_step = step.value

        if extra_data:
            if "classification_result" in extra_data:
                self.state.classification_result = extra_data["classification_result"]
            if "extraction_counts" in extra_data:
                self.state.extraction_counts.update(extra_data["extraction_counts"])
            if "error" in extra_data:
                self.state.last_error = extra_data["error"]

        # Persist to document
        self.document.checkpoint_state = self.state.to_dict()
        self.document.checkpoint_step = step.value
        self.document.checkpoint_timestamp = datetime.utcnow()

        await self.db.commit()
        logger.debug(
            f"Checkpoint saved for document {self.document.id}: "
            f"step={step.value}, completed={completed}"
        )

    async def save_interrupt_state(
        self,
        step: ProcessingStep,
        error: str | None = None,
    ) -> None:
        """Save state when interrupted (SIGTERM, error, timeout).

        This is called when processing cannot continue but we want to
        preserve progress for later resumption.

        Args:
            step: The step where interruption occurred.
            error: Optional error message to record.
        """
        self.state.interrupted_at_step = step.value
        if error:
            self.state.last_error = error

        self.document.checkpoint_state = self.state.to_dict()
        self.document.checkpoint_step = step.value
        self.document.checkpoint_timestamp = datetime.utcnow()

        await self.db.commit()
        logger.info(
            f"Interrupt state saved for document {self.document.id}: "
            f"step={step.value}, error={error}"
        )

    def get_resume_step(self) -> ProcessingStep:
        """Determine which step to resume from.

        Returns:
            The first step that hasn't been completed yet.
        """
        for step in ProcessingStep.ordered_steps():
            if not self.state.is_step_completed(step):
                return step
        return ProcessingStep.COMPLETE

    def is_resuming(self) -> bool:
        """Check if this is a resumed processing run (not fresh start)."""
        return len(self.state.completed_steps) > 0

    async def clear_checkpoint(self) -> None:
        """Clear checkpoint state after successful completion.

        Called when document processing completes successfully to clean up
        the checkpoint data. The processing_logs are preserved for audit.
        """
        self.document.checkpoint_state = None
        self.document.checkpoint_step = None
        self.document.checkpoint_timestamp = None
        await self.db.commit()
        logger.debug(f"Checkpoint cleared for document {self.document.id}")

    async def increment_attempt(self) -> int:
        """Increment and return the processing attempt counter."""
        self.document.processing_attempt += 1
        await self.db.commit()
        return self.document.processing_attempt


def restore_classification_from_checkpoint(cached_result: dict | None) -> Any:
    """Restore classification result from cached checkpoint data.

    Creates a mock object with the same attributes as the LLM classification
    response, allowing the pipeline to skip the expensive classification step
    when resuming.

    Args:
        cached_result: Classification data from checkpoint state.

    Returns:
        Object with classification attributes (classification, confidence, etc.)

    Raises:
        ValueError: If cached_result is None.
    """
    if not cached_result:
        raise ValueError("No cached classification result in checkpoint")

    from types import SimpleNamespace

    # Reconstruct detected_entities
    entities_data = cached_result.get("detected_entities", {})
    entities = SimpleNamespace(
        companies=entities_data.get("companies", []),
        job_titles=entities_data.get("job_titles", []),
        skills=entities_data.get("skills", []),
        dates=entities_data.get("dates", []),
    )

    return SimpleNamespace(
        classification=cached_result["classification"],
        confidence=cached_result["confidence"],
        reasoning=cached_result.get("reasoning", ""),
        has_experiences=cached_result.get("has_experiences", False),
        has_projects=cached_result.get("has_projects", False),
        detected_entities=entities,
    )
