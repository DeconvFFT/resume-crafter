"""FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config import get_settings
from src.models.schemas.common import ErrorResponse, HealthResponse
from src.storage.database import close_db, init_db

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    import logging
    logger = logging.getLogger(__name__)

    # Startup
    await init_db()

    # Start the cron scheduler for automation jobs
    from src.core.scheduler import start_scheduler, stop_scheduler
    try:
        await start_scheduler()
        logger.info("Cron scheduler started successfully")
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {e}")

    yield

    # Shutdown
    try:
        await stop_scheduler()
        logger.info("Cron scheduler stopped")
    except Exception as e:
        logger.warning(f"Error stopping scheduler: {e}")

    await close_db()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Multi-user resume crafting system with intelligent job matching",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - Allow all origins in development
# Note: allow_credentials must be False when using wildcard origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)


# Correlation ID middleware
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all requests."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions with standardized error response."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    error_response = ErrorResponse(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        detail=str(exc) if settings.debug else None,
        correlation_id=correlation_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


# Health check endpoints
@app.get("/health/live", tags=["Health"])
async def health_live() -> dict[str, str]:
    """Liveness probe - is the service running?"""
    return {"status": "alive"}


@app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
async def health_ready() -> HealthResponse:
    """Readiness probe - is the service ready to accept traffic?"""
    # TODO: Implement actual health checks for dependencies
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        database="connected",
        redis="connected",
        chromadb="connected",
    )


# Import and include routers
from src.auth.routes import router as auth_router
from src.api.routes.profile import router as profile_router
from src.api.routes.documents import router as documents_router
from src.api.routes.experiences import router as experiences_router
from src.api.routes.projects import router as projects_router
from src.api.routes.skills import router as skills_router
from src.api.routes.publications import router as publications_router
from src.api.routes.jobs import router as jobs_router
from src.api.routes.resume import router as resume_router
from src.api.routes.tasks import router as tasks_router
from src.api.routes.sse import router as sse_router
from src.api.routes.automation import router as automation_router

app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(profile_router, prefix="/profile", tags=["Profile"])
app.include_router(documents_router, prefix="/documents", tags=["Documents"])
app.include_router(experiences_router, prefix="/experiences", tags=["Experiences"])
app.include_router(projects_router, prefix="/projects", tags=["Projects"])
app.include_router(skills_router, prefix="/skills", tags=["Skills"])
app.include_router(publications_router, prefix="/publications", tags=["Publications"])
app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
app.include_router(resume_router, prefix="/resume", tags=["Resume"])
app.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
app.include_router(sse_router, prefix="/sse", tags=["SSE"])
app.include_router(automation_router, prefix="/automation", tags=["Automation"])


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Resume Crafter API", "version": "0.1.0"}
