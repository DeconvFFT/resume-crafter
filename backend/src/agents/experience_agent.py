"""Experience extraction agent with validation and refinement.

Extracts work experiences from documents with:
- Date validation
- Company/role verification
- Duplicate detection
- Bullet point quality scoring
"""

import logging
from typing import Any

from src.models.schemas.llm_outputs import ExperienceExtractionResult

from .base import BaseAgent, AgentContext, ValidationIssue

logger = logging.getLogger(__name__)


class ExperienceAgent(BaseAgent[ExperienceExtractionResult]):
    """Agent for extracting and validating work experiences."""

    def __init__(self, llm_client: Any = None):
        super().__init__(
            name="ExperienceAgent",
            description="Extracts work experiences with validation",
            llm_client=llm_client,
        )

    async def extract(self, context: AgentContext) -> ExperienceExtractionResult | None:
        """Extract experiences from document."""
        if not self._llm:
            raise ValueError("LLM client not set")

        logger.info(f"Extracting experiences from document {context.document_id}")
        return await self._llm.extract_experiences(context.document_text)

    async def validate(
        self,
        data: ExperienceExtractionResult,
        context: AgentContext,
    ) -> list[ValidationIssue]:
        """Validate extracted experiences."""
        issues = []

        for i, exp in enumerate(data.experiences):
            exp_prefix = f"experiences[{i}]"

            # Validate dates
            if exp.start_date:
                date_result = await self.call_tool(
                    "validate_date_range",
                    {
                        "start_date": exp.start_date,
                        "end_date": exp.end_date,
                        "is_current": exp.is_current,
                    },
                    context,
                )
                if date_result.is_success and date_result.data:
                    for date_issue in date_result.data.get("issues", []):
                        issues.append(ValidationIssue(
                            field=f"{exp_prefix}.dates",
                            message=date_issue,
                            severity="warning",
                        ))

            # Check for project-like entries
            if self._is_likely_project(exp.company, exp.role):
                issues.append(ValidationIssue(
                    field=f"{exp_prefix}.company",
                    message=f"'{exp.company}' looks like a project, not an employer",
                    severity="error",
                    suggestion="Remove this entry or move to projects",
                ))

            # Validate bullets
            for j, bullet in enumerate(exp.bullets):
                # Check bullet quality
                improvement_result = await self.call_tool(
                    "suggest_improvements",
                    {
                        "bullet": bullet.content,
                        "context": f"{exp.role} at {exp.company}",
                    },
                    context,
                )
                if improvement_result.is_success and improvement_result.data:
                    score = improvement_result.data.get("score", 100)
                    if score < 50:
                        issues.append(ValidationIssue(
                            field=f"{exp_prefix}.bullets[{j}]",
                            message=f"Bullet quality score: {score}/100",
                            severity="warning",
                            suggestion="; ".join(
                                s["message"] for s in improvement_result.data.get("suggestions", [])
                            ),
                        ))

                # Check for duplicates
                dup_result = await self.call_tool(
                    "check_duplicate_content",
                    {
                        "content": bullet.content,
                        "user_id": str(context.user_id),
                        "similarity_threshold": 0.85,
                    },
                    context,
                )
                if dup_result.is_success and dup_result.data and dup_result.data.get("is_duplicate"):
                    issues.append(ValidationIssue(
                        field=f"{exp_prefix}.bullets[{j}]",
                        message="This bullet is very similar to existing content",
                        severity="warning",
                    ))

        return issues

    async def refine(
        self,
        data: ExperienceExtractionResult,
        issues: list[ValidationIssue],
        context: AgentContext,
    ) -> ExperienceExtractionResult:
        """Refine extraction based on validation issues.

        For now, we filter out problematic entries rather than re-extracting.
        Future: Use LLM to fix specific issues.
        """
        # Filter out experiences flagged as projects
        project_like_indices = set()
        for issue in issues:
            if "looks like a project" in issue.message:
                # Extract index from field like "experiences[0].company"
                try:
                    idx = int(issue.field.split("[")[1].split("]")[0])
                    project_like_indices.add(idx)
                except (IndexError, ValueError):
                    pass

        if project_like_indices:
            filtered_experiences = [
                exp for i, exp in enumerate(data.experiences)
                if i not in project_like_indices
            ]
            logger.info(
                f"Filtered {len(project_like_indices)} project-like entries from experiences"
            )
            return ExperienceExtractionResult(experiences=filtered_experiences)

        return data

    def _is_likely_project(self, company: str, role: str) -> bool:
        """Check if an entry is likely a project, not employment."""
        company_lower = company.lower().strip()
        role_lower = role.lower().strip()

        project_patterns = [
            "personal project", "side project", "hobby project",
            "academic project", "course project", "portfolio",
            "freelance", "self-employed", "independent",
            "open source", "github", "n/a", "none", "-", "project",
        ]

        for pattern in project_patterns:
            if pattern in company_lower:
                return True

        # Descriptive company names (likely project names)
        descriptive_words = [
            "platform", "application", "system", "tool",
            "website", "app", "bot", "dashboard",
        ]
        words = company_lower.split()
        if len(words) >= 2:
            for word in descriptive_words:
                if word in company_lower and not any(
                    suffix in company_lower
                    for suffix in ["inc", "llc", "ltd", "corp", "co.", "company"]
                ):
                    return True

        # Project-like roles
        project_roles = ["creator", "maintainer", "contributor", "author", "builder"]
        for proj_role in project_roles:
            if proj_role in role_lower and "lead" not in role_lower:
                return True

        return False
