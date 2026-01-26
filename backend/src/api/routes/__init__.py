"""API route modules."""

from src.api.routes.automation import router as automation_router
from src.api.routes.documents import router as documents_router
from src.api.routes.experiences import router as experiences_router
from src.api.routes.jobs import router as jobs_router
from src.api.routes.profile import router as profile_router
from src.api.routes.projects import router as projects_router
from src.api.routes.publications import router as publications_router
from src.api.routes.resume import router as resume_router
from src.api.routes.skills import router as skills_router
from src.api.routes.sse import router as sse_router
from src.api.routes.tasks import router as tasks_router

__all__ = [
    "automation_router",
    "documents_router",
    "experiences_router",
    "jobs_router",
    "profile_router",
    "projects_router",
    "publications_router",
    "resume_router",
    "skills_router",
    "sse_router",
    "tasks_router",
]
