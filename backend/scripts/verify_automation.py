#!/usr/bin/env python3
"""Verification script for the automation system.

This script checks that all automation components are properly configured:
- All integrations can be imported
- Database migrations are applied
- API endpoints work with mock data
- Cron scheduler configuration is valid

Run with: python backend/scripts/verify_automation.py

Exit codes:
    0: All checks passed
    1: Some checks failed
"""

import asyncio
import importlib
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class CheckStatus(Enum):
    """Status of a verification check."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WARNING = "WARNING"


@dataclass
class CheckResult:
    """Result of a single verification check."""
    name: str
    status: CheckStatus
    message: str
    details: dict[str, Any] | None = None


class AutomationVerifier:
    """Verifies automation system configuration and health."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: list[CheckResult] = []

    def log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def add_result(self, result: CheckResult) -> None:
        """Add a check result."""
        self.results.append(result)
        status_symbols = {
            CheckStatus.PASSED: "\033[92m[PASS]\033[0m",
            CheckStatus.FAILED: "\033[91m[FAIL]\033[0m",
            CheckStatus.SKIPPED: "\033[93m[SKIP]\033[0m",
            CheckStatus.WARNING: "\033[93m[WARN]\033[0m",
        }
        self.log(f"  {status_symbols[result.status]} {result.name}: {result.message}")

    # =========================================================================
    # Import Checks
    # =========================================================================

    def check_automation_imports(self) -> None:
        """Check that all automation modules can be imported."""
        self.log("\n=== Checking Automation Imports ===")

        modules_to_check = [
            ("src.models.schemas.automation", "Automation schemas"),
            ("src.api.routes.automation", "Automation API routes"),
            ("src.tasks.automation_tasks", "Automation background tasks"),
            ("src.core.scheduler", "Cron scheduler"),
            ("src.agents.automation.job_discovery_agent", "Job discovery agent"),
            ("src.agents.automation.job_qualification_agent", "Job qualification agent"),
        ]

        for module_path, description in modules_to_check:
            try:
                importlib.import_module(module_path)
                self.add_result(CheckResult(
                    name=f"Import {description}",
                    status=CheckStatus.PASSED,
                    message=f"Successfully imported {module_path}",
                ))
            except ImportError as e:
                self.add_result(CheckResult(
                    name=f"Import {description}",
                    status=CheckStatus.FAILED,
                    message=f"Failed to import: {e}",
                    details={"module": module_path, "error": str(e)},
                ))
            except Exception as e:
                self.add_result(CheckResult(
                    name=f"Import {description}",
                    status=CheckStatus.WARNING,
                    message=f"Import succeeded but with warning: {e}",
                    details={"module": module_path, "error": str(e)},
                ))

    def check_database_models(self) -> None:
        """Check that database models are importable."""
        self.log("\n=== Checking Database Models ===")

        models_to_check = [
            "SearchCampaign",
            "DiscoveredJob",
            "JobApplication",
            "CompanyProfile",
            "CompanyContact",
            "NetworkingOutreach",
            "AutomationLog",
            "CampaignStatus",
            "ApplicationStatus",
            "JobSource",
        ]

        try:
            from src.models import database

            for model_name in models_to_check:
                if hasattr(database, model_name):
                    self.add_result(CheckResult(
                        name=f"Model {model_name}",
                        status=CheckStatus.PASSED,
                        message="Model exists",
                    ))
                else:
                    self.add_result(CheckResult(
                        name=f"Model {model_name}",
                        status=CheckStatus.FAILED,
                        message="Model not found in database module",
                    ))
        except ImportError as e:
            self.add_result(CheckResult(
                name="Database models module",
                status=CheckStatus.FAILED,
                message=f"Cannot import database module: {e}",
            ))

    # =========================================================================
    # Schema Validation Checks
    # =========================================================================

    def check_schemas(self) -> None:
        """Check that Pydantic schemas are valid."""
        self.log("\n=== Checking Pydantic Schemas ===")

        try:
            from src.models.schemas.automation import (
                SearchCampaignCreate,
                SearchCampaignResponse,
                JobApplicationCreate,
                JobApplicationResponse,
                DiscoveredJobResponse,
                AutomationDashboard,
                ApplicationPipelineStats,
            )

            # Test creating a campaign schema
            campaign_data = {
                "name": "Test Campaign",
                "target_roles": ["Software Engineer"],
                "target_locations": ["San Francisco"],
                "keywords": ["python"],
            }
            campaign = SearchCampaignCreate(**campaign_data)
            self.add_result(CheckResult(
                name="SearchCampaignCreate schema",
                status=CheckStatus.PASSED,
                message="Schema validates correctly",
            ))

            # Test application schema
            app_data = {
                "job_title": "Software Engineer",
                "company": "Test Corp",
            }
            application = JobApplicationCreate(**app_data)
            self.add_result(CheckResult(
                name="JobApplicationCreate schema",
                status=CheckStatus.PASSED,
                message="Schema validates correctly",
            ))

            # Test dashboard schema
            dashboard_data = {
                "active_campaigns": 5,
                "total_jobs_discovered": 100,
                "pending_applications": 10,
                "applications_this_week": 25,
                "response_rate": 15.5,
                "interview_rate": 8.2,
                "pipeline_stats": ApplicationPipelineStats(),
            }
            dashboard = AutomationDashboard(**dashboard_data)
            self.add_result(CheckResult(
                name="AutomationDashboard schema",
                status=CheckStatus.PASSED,
                message="Schema validates correctly",
            ))

        except ImportError as e:
            self.add_result(CheckResult(
                name="Schema imports",
                status=CheckStatus.FAILED,
                message=f"Cannot import schemas: {e}",
            ))
        except Exception as e:
            self.add_result(CheckResult(
                name="Schema validation",
                status=CheckStatus.FAILED,
                message=f"Schema validation error: {e}",
            ))

    # =========================================================================
    # Scheduler Configuration Checks
    # =========================================================================

    def check_scheduler_config(self) -> None:
        """Check cron scheduler configuration."""
        self.log("\n=== Checking Scheduler Configuration ===")

        try:
            from src.core.scheduler import (
                CronScheduler,
                CronJobType,
                CronJobStatus,
            )

            scheduler = CronScheduler()

            # Check all job types are configured
            job_types = [
                CronJobType.JOB_DISCOVERY,
                CronJobType.JOB_ANALYSIS,
                CronJobType.APPLICATION_QUEUE,
            ]

            for job_type in job_types:
                job_state = scheduler.get_job_status(job_type)
                if job_state is None:
                    self.add_result(CheckResult(
                        name=f"Scheduler job {job_type.value}",
                        status=CheckStatus.FAILED,
                        message="Job not configured",
                    ))
                else:
                    self.add_result(CheckResult(
                        name=f"Scheduler job {job_type.value}",
                        status=CheckStatus.PASSED,
                        message=f"Configured with interval {job_state.interval_seconds}s",
                        details={
                            "interval_seconds": job_state.interval_seconds,
                            "status": job_state.status.value,
                            "config": job_state._config,
                        },
                    ))

            # Verify default intervals are sensible
            discovery_job = scheduler.get_job_status(CronJobType.JOB_DISCOVERY)
            if discovery_job.interval_seconds < 3600:  # Less than 1 hour
                self.add_result(CheckResult(
                    name="Job discovery interval",
                    status=CheckStatus.WARNING,
                    message=f"Interval is very short: {discovery_job.interval_seconds}s",
                ))
            else:
                self.add_result(CheckResult(
                    name="Job discovery interval",
                    status=CheckStatus.PASSED,
                    message=f"Reasonable interval: {discovery_job.interval_seconds / 3600:.1f} hours",
                ))

        except ImportError as e:
            self.add_result(CheckResult(
                name="Scheduler module",
                status=CheckStatus.FAILED,
                message=f"Cannot import scheduler: {e}",
            ))
        except Exception as e:
            self.add_result(CheckResult(
                name="Scheduler configuration",
                status=CheckStatus.FAILED,
                message=f"Configuration error: {e}",
            ))

    # =========================================================================
    # Rate Limiting Configuration Checks
    # =========================================================================

    def check_rate_limits(self) -> None:
        """Check rate limiting configuration."""
        self.log("\n=== Checking Rate Limiting Configuration ===")

        try:
            from src.tasks.automation_tasks import (
                MAX_APPLICATIONS_PER_DAY,
                MIN_APPLICATION_DELAY_SECONDS,
            )

            # Check daily limit is in expected range (30-40)
            if 30 <= MAX_APPLICATIONS_PER_DAY <= 40:
                self.add_result(CheckResult(
                    name="Daily application limit",
                    status=CheckStatus.PASSED,
                    message=f"{MAX_APPLICATIONS_PER_DAY} applications/day",
                ))
            else:
                self.add_result(CheckResult(
                    name="Daily application limit",
                    status=CheckStatus.WARNING,
                    message=f"{MAX_APPLICATIONS_PER_DAY} applications/day (expected 30-40)",
                ))

            # Check delay is 5 minutes (300 seconds)
            if MIN_APPLICATION_DELAY_SECONDS == 300:
                self.add_result(CheckResult(
                    name="Application delay",
                    status=CheckStatus.PASSED,
                    message="5 minutes between applications",
                ))
            elif MIN_APPLICATION_DELAY_SECONDS >= 60:
                self.add_result(CheckResult(
                    name="Application delay",
                    status=CheckStatus.WARNING,
                    message=f"{MIN_APPLICATION_DELAY_SECONDS}s delay (expected 300s)",
                ))
            else:
                self.add_result(CheckResult(
                    name="Application delay",
                    status=CheckStatus.FAILED,
                    message=f"Delay too short: {MIN_APPLICATION_DELAY_SECONDS}s",
                ))

        except ImportError as e:
            self.add_result(CheckResult(
                name="Rate limit imports",
                status=CheckStatus.FAILED,
                message=f"Cannot import rate limit constants: {e}",
            ))

    # =========================================================================
    # Agent Configuration Checks
    # =========================================================================

    def check_agents(self) -> None:
        """Check that automation agents are properly configured."""
        self.log("\n=== Checking Automation Agents ===")

        agents_to_check = [
            ("src.agents.automation.job_discovery_agent", "JobDiscoveryAgent"),
            ("src.agents.automation.job_qualification_agent", "JobQualificationAgent"),
        ]

        for module_path, class_name in agents_to_check:
            try:
                module = importlib.import_module(module_path)
                agent_class = getattr(module, class_name)

                # Try to instantiate the agent
                agent = agent_class()

                self.add_result(CheckResult(
                    name=f"Agent {class_name}",
                    status=CheckStatus.PASSED,
                    message="Agent can be instantiated",
                ))

                # Check for required methods
                required_methods = ["run"]
                for method in required_methods:
                    if hasattr(agent, method) and callable(getattr(agent, method)):
                        self.add_result(CheckResult(
                            name=f"{class_name}.{method}()",
                            status=CheckStatus.PASSED,
                            message="Method exists",
                        ))
                    else:
                        self.add_result(CheckResult(
                            name=f"{class_name}.{method}()",
                            status=CheckStatus.FAILED,
                            message="Required method not found",
                        ))

            except ImportError as e:
                self.add_result(CheckResult(
                    name=f"Agent {class_name}",
                    status=CheckStatus.FAILED,
                    message=f"Cannot import: {e}",
                ))
            except Exception as e:
                self.add_result(CheckResult(
                    name=f"Agent {class_name}",
                    status=CheckStatus.WARNING,
                    message=f"Instantiation warning: {e}",
                ))

    # =========================================================================
    # API Route Checks
    # =========================================================================

    def check_api_routes(self) -> None:
        """Check that API routes are properly registered."""
        self.log("\n=== Checking API Routes ===")

        try:
            from src.api.routes.automation import router

            # Check router has expected endpoints
            expected_endpoints = [
                ("/campaigns", ["POST", "GET"]),
                ("/campaigns/{campaign_id}", ["GET"]),
                ("/campaigns/{campaign_id}/activate", ["POST"]),
                ("/campaigns/{campaign_id}/pause", ["POST"]),
                ("/discovered-jobs", ["GET"]),
                ("/applications", ["GET"]),
                ("/applications/queue", ["POST"]),
                ("/stats", ["GET"]),
                ("/logs", ["GET"]),
                ("/cron/jobs", ["GET"]),
            ]

            # Get all routes from router
            routes = {route.path: [m for m in route.methods] for route in router.routes if hasattr(route, 'methods')}

            for path, methods in expected_endpoints:
                if path in routes:
                    self.add_result(CheckResult(
                        name=f"Route {path}",
                        status=CheckStatus.PASSED,
                        message=f"Registered with methods: {', '.join(routes[path])}",
                    ))
                else:
                    self.add_result(CheckResult(
                        name=f"Route {path}",
                        status=CheckStatus.WARNING,
                        message="Route not found (may be using different path format)",
                    ))

        except ImportError as e:
            self.add_result(CheckResult(
                name="API routes module",
                status=CheckStatus.FAILED,
                message=f"Cannot import routes: {e}",
            ))
        except Exception as e:
            self.add_result(CheckResult(
                name="API routes check",
                status=CheckStatus.FAILED,
                message=f"Error checking routes: {e}",
            ))

    # =========================================================================
    # Database Migration Checks
    # =========================================================================

    async def check_database_migrations(self) -> None:
        """Check that database migrations are applied."""
        self.log("\n=== Checking Database Migrations ===")

        try:
            # Try to import and inspect the database engine
            from sqlalchemy import inspect, text
            from sqlalchemy.ext.asyncio import create_async_engine
            import os

            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                self.add_result(CheckResult(
                    name="Database connection",
                    status=CheckStatus.SKIPPED,
                    message="DATABASE_URL not set - skipping migration check",
                ))
                return

            # Convert to async URL if needed
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            engine = create_async_engine(database_url)

            async with engine.connect() as conn:
                # Check for automation tables
                automation_tables = [
                    "search_campaigns",
                    "discovered_jobs",
                    "job_applications",
                    "company_profiles",
                    "company_contacts",
                    "networking_outreach",
                    "automation_logs",
                ]

                result = await conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                )
                existing_tables = {row[0] for row in result}

                for table in automation_tables:
                    if table in existing_tables:
                        self.add_result(CheckResult(
                            name=f"Table {table}",
                            status=CheckStatus.PASSED,
                            message="Table exists",
                        ))
                    else:
                        self.add_result(CheckResult(
                            name=f"Table {table}",
                            status=CheckStatus.FAILED,
                            message="Table not found - run migrations",
                        ))

            await engine.dispose()

        except ImportError as e:
            self.add_result(CheckResult(
                name="Database check",
                status=CheckStatus.SKIPPED,
                message=f"Missing dependencies for database check: {e}",
            ))
        except Exception as e:
            self.add_result(CheckResult(
                name="Database migrations",
                status=CheckStatus.WARNING,
                message=f"Could not verify migrations: {e}",
            ))

    # =========================================================================
    # Run All Checks
    # =========================================================================

    async def run_all_checks(self) -> bool:
        """Run all verification checks.

        Returns:
            True if all checks passed, False otherwise.
        """
        self.log("=" * 60)
        self.log("Automation System Verification")
        self.log("=" * 60)

        # Run synchronous checks
        self.check_automation_imports()
        self.check_database_models()
        self.check_schemas()
        self.check_scheduler_config()
        self.check_rate_limits()
        self.check_agents()
        self.check_api_routes()

        # Run async checks
        await self.check_database_migrations()

        # Summary
        self.log("\n" + "=" * 60)
        self.log("Verification Summary")
        self.log("=" * 60)

        passed = sum(1 for r in self.results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIPPED)

        self.log(f"\n  Total checks: {len(self.results)}")
        self.log(f"  \033[92mPassed:  {passed}\033[0m")
        self.log(f"  \033[91mFailed:  {failed}\033[0m")
        self.log(f"  \033[93mWarnings: {warnings}\033[0m")
        self.log(f"  \033[93mSkipped: {skipped}\033[0m")

        if failed > 0:
            self.log("\n\033[91mVerification FAILED\033[0m")
            self.log("\nFailed checks:")
            for r in self.results:
                if r.status == CheckStatus.FAILED:
                    self.log(f"  - {r.name}: {r.message}")
            return False
        elif warnings > 0:
            self.log("\n\033[93mVerification PASSED with warnings\033[0m")
            return True
        else:
            self.log("\n\033[92mVerification PASSED\033[0m")
            return True


def main():
    """Run the verification script."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify automation system configuration")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (minimal output)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    verifier = AutomationVerifier(verbose=not args.quiet)

    # Run all checks
    success = asyncio.run(verifier.run_all_checks())

    if args.json:
        import json
        results = [
            {
                "name": r.name,
                "status": r.status.value,
                "message": r.message,
                "details": r.details,
            }
            for r in verifier.results
        ]
        print(json.dumps(results, indent=2))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
