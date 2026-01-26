"""ARQ background tasks."""

from .document_tasks import process_document
from .job_tasks import analyze_job
from .matching_tasks import generate_match
from .worker import WorkerSettings

# Automation tasks
from .automation_tasks import (
    discover_jobs,
    analyze_discovered_job,
    batch_analyze_jobs,
    process_application_queue,
    research_company,
    generate_outreach,
    batch_generate_outreach,
    run_scheduled_discovery,
    run_scheduled_analysis,
    run_scheduled_queue_processing,
)

__all__ = [
    # Document processing
    "process_document",
    "analyze_job",
    "generate_match",
    "WorkerSettings",
    # Automation tasks
    "discover_jobs",
    "analyze_discovered_job",
    "batch_analyze_jobs",
    "process_application_queue",
    "research_company",
    "generate_outreach",
    "batch_generate_outreach",
    "run_scheduled_discovery",
    "run_scheduled_analysis",
    "run_scheduled_queue_processing",
]
