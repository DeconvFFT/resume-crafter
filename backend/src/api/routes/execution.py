"""Execution monitoring endpoints for workflow tracking.

Provides real-time monitoring and control of automated workflows including
job discovery, analysis, and application processing.

Usage:
    # List executions
    GET /api/automation/executions?status=running&workflow_type=job_discovery

    # Get execution details with step progress
    GET /api/automation/executions/{id}

    # Cancel running execution
    POST /api/automation/executions/{id}/cancel

    # Stream execution logs via SSE
    GET /api/automation/executions/{id}/logs?token=<jwt>
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.auth.dependencies import CurrentUser, get_user_from_token_query
from src.models.database import User
from src.models.schemas.execution import (
    ExecutionCancelRequest,
    ExecutionCancelResponse,
    ExecutionDetailResponse,
    ExecutionFilter,
    ExecutionListResponse,
    ExecutionLogEntry,
    ExecutionLogListResponse,
    ExecutionResponse,
    ExecutionSSEEvent,
    ExecutionStatus,
    ExecutionStepResponse,
    LogLevel,
    WorkflowType,
)
from src.storage.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ In-Memory Execution Store ============
# Note: In production, this should be replaced with proper database models
# This is a temporary implementation for the API structure

_executions: dict[str, dict] = {}
_execution_steps: dict[str, list[dict]] = {}
_execution_logs: dict[str, list[dict]] = {}


async def _get_execution(
    execution_id: UUID,
    user: User,
) -> dict | None:
    """Get execution by ID if user has access."""
    execution = _executions.get(str(execution_id))
    if execution and execution.get("user_id") == str(user.id):
        return execution
    return None


async def _verify_execution_access(
    execution_id: UUID,
    user: User,
) -> dict:
    """Verify user has access to execution and return it."""
    execution = await _get_execution(execution_id, user)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )
    return execution


# ============ Execution Endpoints ============


@router.get(
    "",
    response_model=ExecutionListResponse,
    summary="List workflow executions",
    description="""
    List all workflow executions for the current user with optional filters.

    **Filters:**
    - `workflow_type`: Filter by workflow type (job_discovery, job_analysis, etc.)
    - `status`: Filter by execution status (pending, running, completed, failed, cancelled)
    - `campaign_id`: Filter by campaign ID
    - `started_after`: Filter executions started after this timestamp
    - `started_before`: Filter executions started before this timestamp

    Results are paginated and sorted by creation date (newest first).
    """,
)
async def list_executions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    workflow_type: WorkflowType | None = Query(None, description="Filter by workflow type"),
    execution_status: ExecutionStatus | None = Query(
        None, alias="status", description="Filter by execution status"
    ),
    campaign_id: str | None = Query(None, description="Filter by campaign ID"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    started_after: datetime | None = Query(None, description="Filter by start time (after)"),
    started_before: datetime | None = Query(None, description="Filter by start time (before)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> ExecutionListResponse:
    """List executions with filters."""
    user_id = str(current_user.id)

    # Ensure sample executions exist for development/demo (creates if none exist)
    ensure_sample_executions_for_user(user_id)

    # Filter executions
    filtered = [
        ex for ex in _executions.values()
        if ex.get("user_id") == user_id
    ]

    # Apply filters
    if workflow_type:
        filtered = [ex for ex in filtered if ex.get("workflow_type") == workflow_type.value]

    if execution_status:
        filtered = [ex for ex in filtered if ex.get("status") == execution_status.value]

    if campaign_id:
        filtered = [ex for ex in filtered if ex.get("campaign_id") == campaign_id]

    if entity_id:
        filtered = [ex for ex in filtered if ex.get("entity_id") == entity_id]

    if started_after:
        filtered = [
            ex for ex in filtered
            if ex.get("started_at") and datetime.fromisoformat(ex["started_at"]) >= started_after
        ]

    if started_before:
        filtered = [
            ex for ex in filtered
            if ex.get("started_at") and datetime.fromisoformat(ex["started_at"]) <= started_before
        ]

    # Sort by created_at descending
    filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Paginate
    total = len(filtered)
    pages = (total + page_size - 1) // page_size if total > 0 else 0
    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return ExecutionListResponse(
        items=[ExecutionResponse(**ex) for ex in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{execution_id}",
    response_model=ExecutionDetailResponse,
    summary="Get execution details",
    description="""
    Get detailed information about a specific execution including:
    - Current status and progress
    - Individual step status and timing
    - Recent log entries
    - Error information if failed
    """,
)
async def get_execution(
    execution_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    include_logs: bool = Query(True, description="Include recent log entries"),
    log_limit: int = Query(50, ge=1, le=200, description="Maximum number of logs to return"),
) -> ExecutionDetailResponse:
    """Get execution details with steps and logs."""
    execution = await _verify_execution_access(execution_id, current_user)

    # Get steps
    steps = _execution_steps.get(str(execution_id), [])

    # Get recent logs if requested
    recent_logs = []
    if include_logs:
        logs = _execution_logs.get(str(execution_id), [])
        recent_logs = logs[-log_limit:] if logs else []

    return ExecutionDetailResponse(
        **execution,
        steps=[ExecutionStepResponse(**step) for step in steps],
        recent_logs=[ExecutionLogEntry(**log) for log in recent_logs],
    )


@router.post(
    "/{execution_id}/cancel",
    response_model=ExecutionCancelResponse,
    summary="Cancel running execution",
    description="""
    Cancel a running or pending execution.

    This will:
    - Mark the execution as cancelled
    - Stop any running steps
    - Record the cancellation reason

    Note: Already completed or failed executions cannot be cancelled.
    """,
)
async def cancel_execution(
    execution_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: ExecutionCancelRequest | None = None,
) -> ExecutionCancelResponse:
    """Cancel a running execution."""
    execution = await _verify_execution_access(execution_id, current_user)

    # Check if can be cancelled
    current_status = execution.get("status")
    if current_status in [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value, ExecutionStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel execution with status: {current_status}",
        )

    # Update execution status
    cancelled_at = datetime.utcnow()
    execution["status"] = ExecutionStatus.CANCELLED.value
    execution["completed_at"] = cancelled_at.isoformat()
    execution["error_message"] = request.reason if request else "Cancelled by user"
    execution["updated_at"] = cancelled_at.isoformat()

    # Add cancellation log
    log_entry = {
        "id": str(UUID(int=len(_execution_logs.get(str(execution_id), [])) + 1)),
        "execution_id": str(execution_id),
        "step_id": None,
        "level": LogLevel.INFO.value,
        "message": f"Execution cancelled: {request.reason if request else 'Cancelled by user'}",
        "data": {"cancelled_by": str(current_user.id)},
        "timestamp": cancelled_at.isoformat(),
    }

    if str(execution_id) not in _execution_logs:
        _execution_logs[str(execution_id)] = []
    _execution_logs[str(execution_id)].append(log_entry)

    logger.info(f"Execution {execution_id} cancelled by user {current_user.id}")

    return ExecutionCancelResponse(
        id=str(execution_id),
        status=ExecutionStatus.CANCELLED,
        cancelled_at=cancelled_at,
        reason=request.reason if request else "Cancelled by user",
    )


@router.get(
    "/{execution_id}/logs",
    response_model=ExecutionLogListResponse,
    summary="Get execution logs",
    description="""
    Get paginated logs for an execution.

    Logs are sorted by timestamp (newest first by default).
    Use `offset` and `limit` for pagination.
    """,
)
async def get_execution_logs(
    execution_id: UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    level: LogLevel | None = Query(None, description="Filter by log level"),
    step_id: str | None = Query(None, description="Filter by step ID"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum logs to return"),
    newest_first: bool = Query(True, description="Sort newest first"),
) -> ExecutionLogListResponse:
    """Get execution logs with filtering and pagination."""
    await _verify_execution_access(execution_id, current_user)

    logs = _execution_logs.get(str(execution_id), [])

    # Apply filters
    if level:
        logs = [log for log in logs if log.get("level") == level.value]

    if step_id:
        logs = [log for log in logs if log.get("step_id") == step_id]

    # Sort
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=newest_first)

    # Paginate
    total = len(logs)
    paginated = logs[offset:offset + limit]
    has_more = offset + limit < total

    return ExecutionLogListResponse(
        items=[ExecutionLogEntry(**log) for log in paginated],
        total=total,
        has_more=has_more,
    )


# ============ SSE Log Streaming ============


async def _generate_execution_log_stream(
    execution_id: UUID,
    execution: dict,
    include_history: bool = True,
):
    """Generate SSE stream for execution logs.

    Args:
        execution_id: The execution ID.
        execution: The execution data.
        include_history: Whether to include existing logs on connect.

    Yields:
        SSE formatted strings.
    """
    # Send initial state with existing logs if requested
    if include_history:
        logs = _execution_logs.get(str(execution_id), [])
        init_event = ExecutionSSEEvent(
            event_type="init",
            execution_id=str(execution_id),
            timestamp=datetime.utcnow().isoformat(),
            data={
                "status": execution.get("status"),
                "progress": execution.get("progress", 0),
                "logs": logs[-50:],  # Last 50 logs
            },
        )
        yield f"data: {init_event.to_sse_data()}\n\n"

    # If already completed or failed, send done event and close
    if execution.get("status") in [
        ExecutionStatus.COMPLETED.value,
        ExecutionStatus.FAILED.value,
        ExecutionStatus.CANCELLED.value,
    ]:
        done_event = ExecutionSSEEvent(
            event_type="done" if execution.get("status") == ExecutionStatus.COMPLETED.value else "error",
            execution_id=str(execution_id),
            timestamp=datetime.utcnow().isoformat(),
            data={
                "status": execution.get("status"),
                "error": execution.get("error_message"),
            },
        )
        yield f"data: {done_event.to_sse_data()}\n\n"
        return

    # Use polling approach for real-time updates from in-memory store
    # This is more reliable than Redis pubsub for this use case
    start_time = asyncio.get_event_loop().time()
    last_heartbeat = start_time
    timeout = 300.0  # 5 minute timeout
    heartbeat_interval = 15.0
    last_log_count = len(_execution_logs.get(str(execution_id), []))

    while True:
        current_time = asyncio.get_event_loop().time()
        if current_time - start_time > timeout:
            logger.info(f"SSE subscription timeout for execution {execution_id}")
            break

        # Send heartbeat if needed
        if current_time - last_heartbeat > heartbeat_interval:
            heartbeat_event = ExecutionSSEEvent(
                event_type="heartbeat",
                execution_id=str(execution_id),
                timestamp=datetime.utcnow().isoformat(),
            )
            yield f"data: {heartbeat_event.to_sse_data()}\n\n"
            last_heartbeat = current_time

        # Check for new logs in the in-memory store
        current_logs = _execution_logs.get(str(execution_id), [])
        if len(current_logs) > last_log_count:
            new_logs = current_logs[last_log_count:]
            for log in new_logs:
                log_event = ExecutionSSEEvent(
                    event_type="log",
                    execution_id=str(execution_id),
                    timestamp=datetime.utcnow().isoformat(),
                    data=log,
                )
                yield f"data: {log_event.to_sse_data()}\n\n"
            last_log_count = len(current_logs)

        # Check for execution status changes
        current_execution = _executions.get(str(execution_id))
        if current_execution and current_execution.get("status") in [
            ExecutionStatus.COMPLETED.value,
            ExecutionStatus.FAILED.value,
            ExecutionStatus.CANCELLED.value,
        ]:
            done_event = ExecutionSSEEvent(
                event_type="done" if current_execution.get("status") == ExecutionStatus.COMPLETED.value else "error",
                execution_id=str(execution_id),
                timestamp=datetime.utcnow().isoformat(),
                data={
                    "status": current_execution.get("status"),
                    "result": current_execution.get("result"),
                    "error": current_execution.get("error_message"),
                },
            )
            yield f"data: {done_event.to_sse_data()}\n\n"
            break

        await asyncio.sleep(0.5)


@router.get(
    "/{execution_id}/stream",
    response_class=StreamingResponse,
    summary="Stream execution events via SSE",
    description="""
    Stream real-time execution events using Server-Sent Events (SSE).

    **Event Types:**
    - `init`: Initial state with existing logs (sent on connect)
    - `log`: New log entry
    - `step_update`: Step status change
    - `status_change`: Execution status change
    - `progress`: Progress percentage update
    - `done`: Execution complete
    - `error`: Execution failed
    - `heartbeat`: Keep-alive (every 15s)

    **Usage (JavaScript):**
    ```javascript
    const eventSource = new EventSource(
        '/api/automation/executions/{id}/stream?token=<jwt>'
    );

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch (data.event_type) {
            case 'log':
                console.log(data.data.message);
                break;
            case 'progress':
                updateProgress(data.data.progress);
                break;
            case 'done':
                eventSource.close();
                break;
        }
    };
    ```

    Note: Token must be passed as query parameter since EventSource
    doesn't support custom headers.
    """,
    responses={
        200: {
            "description": "SSE stream of execution events",
            "content": {"text/event-stream": {}},
        },
        404: {"description": "Execution not found"},
    },
)
async def stream_execution_events(
    execution_id: UUID,
    include_history: bool = Query(
        default=True,
        description="Include existing logs on connect",
    ),
    token: str | None = Query(
        default=None,
        description="JWT access token (for SSE clients that can't send headers)",
    ),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Stream execution events via SSE.

    This endpoint provides real-time updates as an execution progresses.

    Note: EventSource doesn't support custom headers, so we accept the
    access token as a query parameter for SSE clients.
    """
    # Authenticate via query parameter token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required for SSE streaming",
        )

    current_user = await get_user_from_token_query(token, db)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    execution = await _verify_execution_access(execution_id, current_user)

    return StreamingResponse(
        _generate_execution_log_stream(execution_id, execution, include_history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# ============ Helper Functions for Worker Integration ============


async def create_execution(
    user_id: UUID,
    workflow_type: WorkflowType,
    campaign_id: UUID | None = None,
    entity_id: UUID | None = None,
    entity_type: str | None = None,
    config: dict | None = None,
    total_steps: int = 0,
) -> str:
    """Create a new execution record.

    This is called by background workers when starting a workflow.
    """
    from uuid import uuid4

    execution_id = str(uuid4())
    now = datetime.utcnow().isoformat()

    execution = {
        "id": execution_id,
        "user_id": str(user_id),
        "workflow_type": workflow_type.value,
        "status": ExecutionStatus.PENDING.value,
        "campaign_id": str(campaign_id) if campaign_id else None,
        "entity_id": str(entity_id) if entity_id else None,
        "entity_type": entity_type,
        "config": config,
        "progress": 0,
        "current_step": None,
        "total_steps": total_steps,
        "completed_steps": 0,
        "started_at": None,
        "completed_at": None,
        "duration_ms": None,
        "result": None,
        "error_message": None,
        "scheduled_at": None,
        "created_at": now,
        "updated_at": now,
    }

    _executions[execution_id] = execution
    _execution_steps[execution_id] = []
    _execution_logs[execution_id] = []

    return execution_id


async def update_execution_status(
    execution_id: str,
    status: ExecutionStatus,
    progress: int | None = None,
    current_step: str | None = None,
    result: dict | None = None,
    error_message: str | None = None,
) -> None:
    """Update execution status.

    This is called by background workers during workflow execution.
    """
    if execution_id not in _executions:
        return

    execution = _executions[execution_id]
    now = datetime.utcnow()

    execution["status"] = status.value
    execution["updated_at"] = now.isoformat()

    if progress is not None:
        execution["progress"] = progress

    if current_step is not None:
        execution["current_step"] = current_step

    if status == ExecutionStatus.RUNNING and not execution.get("started_at"):
        execution["started_at"] = now.isoformat()

    if status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
        execution["completed_at"] = now.isoformat()
        if execution.get("started_at"):
            started = datetime.fromisoformat(execution["started_at"])
            execution["duration_ms"] = int((now - started).total_seconds() * 1000)

    if result is not None:
        execution["result"] = result

    if error_message is not None:
        execution["error_message"] = error_message


async def add_execution_log(
    execution_id: str,
    level: LogLevel,
    message: str,
    step_id: str | None = None,
    data: dict | None = None,
) -> None:
    """Add a log entry to an execution.

    This is called by background workers during workflow execution.
    """
    from uuid import uuid4

    if execution_id not in _execution_logs:
        _execution_logs[execution_id] = []

    log_entry = {
        "id": str(uuid4()),
        "execution_id": execution_id,
        "step_id": step_id,
        "level": level.value,
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }

    _execution_logs[execution_id].append(log_entry)


# ============ Sample Data Initialization ============


def _create_sample_executions_for_user(user_id: str) -> None:
    """Create sample execution data for a user (for development/demo purposes).

    This is called when a user first accesses the executions endpoint
    and no executions exist for them.
    """
    from uuid import uuid4
    from datetime import timedelta

    now = datetime.utcnow()

    # Sample execution 1: Completed job discovery
    exec_id_1 = str(uuid4())
    started_1 = now - timedelta(hours=2)
    completed_1 = started_1 + timedelta(minutes=15)
    _executions[exec_id_1] = {
        "id": exec_id_1,
        "user_id": user_id,
        "workflow_type": WorkflowType.JOB_DISCOVERY.value,
        "status": ExecutionStatus.COMPLETED.value,
        "campaign_id": None,
        "entity_id": None,
        "entity_type": None,
        "config": {"search_query": "Senior Software Engineer", "location": "Remote"},
        "progress": 100,
        "current_step": "complete",
        "total_steps": 4,
        "completed_steps": 4,
        "started_at": started_1.isoformat(),
        "completed_at": completed_1.isoformat(),
        "duration_ms": int((completed_1 - started_1).total_seconds() * 1000),
        "result": {"jobs_found": 15, "jobs_matched": 8},
        "error_message": None,
        "scheduled_at": None,
        "created_at": started_1.isoformat(),
        "updated_at": completed_1.isoformat(),
    }
    _execution_steps[exec_id_1] = []
    _execution_logs[exec_id_1] = [
        {
            "id": str(uuid4()),
            "execution_id": exec_id_1,
            "step_id": None,
            "level": LogLevel.INFO.value,
            "message": "Job discovery workflow started",
            "data": None,
            "timestamp": started_1.isoformat(),
        },
        {
            "id": str(uuid4()),
            "execution_id": exec_id_1,
            "step_id": None,
            "level": LogLevel.INFO.value,
            "message": "Found 15 matching job postings",
            "data": {"count": 15},
            "timestamp": (started_1 + timedelta(minutes=5)).isoformat(),
        },
        {
            "id": str(uuid4()),
            "execution_id": exec_id_1,
            "step_id": None,
            "level": LogLevel.INFO.value,
            "message": "Job discovery completed successfully",
            "data": {"jobs_found": 15, "jobs_matched": 8},
            "timestamp": completed_1.isoformat(),
        },
    ]

    # Sample execution 2: Running job analysis
    exec_id_2 = str(uuid4())
    started_2 = now - timedelta(minutes=10)
    _executions[exec_id_2] = {
        "id": exec_id_2,
        "user_id": user_id,
        "workflow_type": WorkflowType.JOB_ANALYSIS.value,
        "status": ExecutionStatus.RUNNING.value,
        "campaign_id": None,
        "entity_id": None,
        "entity_type": "job",
        "config": {"job_id": str(uuid4())},
        "progress": 65,
        "current_step": "analyzing_requirements",
        "total_steps": 5,
        "completed_steps": 3,
        "started_at": started_2.isoformat(),
        "completed_at": None,
        "duration_ms": None,
        "result": None,
        "error_message": None,
        "scheduled_at": None,
        "created_at": started_2.isoformat(),
        "updated_at": now.isoformat(),
    }
    _execution_steps[exec_id_2] = []
    _execution_logs[exec_id_2] = [
        {
            "id": str(uuid4()),
            "execution_id": exec_id_2,
            "step_id": None,
            "level": LogLevel.INFO.value,
            "message": "Starting job analysis workflow",
            "data": None,
            "timestamp": started_2.isoformat(),
        },
        {
            "id": str(uuid4()),
            "execution_id": exec_id_2,
            "step_id": None,
            "level": LogLevel.INFO.value,
            "message": "Extracting job requirements",
            "data": None,
            "timestamp": (started_2 + timedelta(minutes=2)).isoformat(),
        },
        {
            "id": str(uuid4()),
            "execution_id": exec_id_2,
            "step_id": None,
            "level": LogLevel.INFO.value,
            "message": "Analyzing skill requirements",
            "data": {"skills_found": 12},
            "timestamp": (started_2 + timedelta(minutes=5)).isoformat(),
        },
    ]

    # Sample execution 3: Failed resume generation
    exec_id_3 = str(uuid4())
    started_3 = now - timedelta(hours=1)
    failed_3 = started_3 + timedelta(minutes=3)
    _executions[exec_id_3] = {
        "id": exec_id_3,
        "user_id": user_id,
        "workflow_type": WorkflowType.RESUME_GENERATION.value,
        "status": ExecutionStatus.FAILED.value,
        "campaign_id": None,
        "entity_id": None,
        "entity_type": "resume_match",
        "config": {"match_id": str(uuid4()), "format": "pdf"},
        "progress": 25,
        "current_step": "generating_content",
        "total_steps": 4,
        "completed_steps": 1,
        "started_at": started_3.isoformat(),
        "completed_at": failed_3.isoformat(),
        "duration_ms": int((failed_3 - started_3).total_seconds() * 1000),
        "result": None,
        "error_message": "Template rendering failed: missing required field 'experience_bullets'",
        "scheduled_at": None,
        "created_at": started_3.isoformat(),
        "updated_at": failed_3.isoformat(),
    }
    _execution_steps[exec_id_3] = []
    _execution_logs[exec_id_3] = [
        {
            "id": str(uuid4()),
            "execution_id": exec_id_3,
            "step_id": None,
            "level": LogLevel.INFO.value,
            "message": "Starting resume generation",
            "data": None,
            "timestamp": started_3.isoformat(),
        },
        {
            "id": str(uuid4()),
            "execution_id": exec_id_3,
            "step_id": None,
            "level": LogLevel.ERROR.value,
            "message": "Template rendering failed: missing required field 'experience_bullets'",
            "data": {"error_type": "ValidationError"},
            "timestamp": failed_3.isoformat(),
        },
    ]

    # Sample execution 4: Pending application processing
    exec_id_4 = str(uuid4())
    created_4 = now - timedelta(minutes=5)
    _executions[exec_id_4] = {
        "id": exec_id_4,
        "user_id": user_id,
        "workflow_type": WorkflowType.APPLICATION_PROCESSING.value,
        "status": ExecutionStatus.PENDING.value,
        "campaign_id": None,
        "entity_id": None,
        "entity_type": "application",
        "config": {"application_ids": [str(uuid4()), str(uuid4())]},
        "progress": 0,
        "current_step": None,
        "total_steps": 3,
        "completed_steps": 0,
        "started_at": None,
        "completed_at": None,
        "duration_ms": None,
        "result": None,
        "error_message": None,
        "scheduled_at": (now + timedelta(minutes=30)).isoformat(),
        "created_at": created_4.isoformat(),
        "updated_at": created_4.isoformat(),
    }
    _execution_steps[exec_id_4] = []
    _execution_logs[exec_id_4] = []

    logger.info(f"Created 4 sample executions for user {user_id}")


def ensure_sample_executions_for_user(user_id: str) -> None:
    """Ensure sample executions exist for a user (called on first access)."""
    # Check if user already has executions
    user_executions = [ex for ex in _executions.values() if ex.get("user_id") == user_id]
    if not user_executions:
        _create_sample_executions_for_user(user_id)
