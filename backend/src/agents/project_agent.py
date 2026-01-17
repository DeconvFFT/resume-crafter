"""Project extraction agent with validation and enrichment.

Extracts projects from documents with:
- URL validation
- GitHub enrichment
- Technology inference
- Bullet point quality scoring
"""

import logging
from typing import Any

from src.models.schemas.llm_outputs import ProjectExtractionResult

from .base import BaseAgent, AgentContext, ValidationIssue

logger = logging.getLogger(__name__)


class ProjectAgent(BaseAgent[ProjectExtractionResult]):
    """Agent for extracting and validating projects."""

    def __init__(self, llm_client: Any = None):
        super().__init__(
            name="ProjectAgent",
            description="Extracts projects with URL validation and enrichment",
            llm_client=llm_client,
        )

    async def extract(self, context: AgentContext) -> ProjectExtractionResult | None:
        """Extract projects from document."""
        if not self._llm:
            raise ValueError("LLM client not set")

        logger.info(f"Extracting projects from document {context.document_id}")
        return await self._llm.extract_projects(context.document_text)

    async def validate(
        self,
        data: ProjectExtractionResult,
        context: AgentContext,
    ) -> list[ValidationIssue]:
        """Validate extracted projects."""
        issues = []

        for i, proj in enumerate(data.projects):
            proj_prefix = f"projects[{i}]"

            # Validate URLs
            for j, link in enumerate(proj.links):
                url = link.get("url", "")
                link_type = link.get("type", "other")

                if url:
                    url_result = await self.call_tool(
                        "validate_url",
                        {"url": url, "expected_type": link_type},
                        context,
                    )
                    if url_result.is_success and url_result.data:
                        if not url_result.data.get("is_valid"):
                            issues.append(ValidationIssue(
                                field=f"{proj_prefix}.links[{j}]",
                                message=f"Invalid URL: {url}",
                                severity="error",
                            ))
                        elif not url_result.data.get("is_accessible"):
                            issues.append(ValidationIssue(
                                field=f"{proj_prefix}.links[{j}]",
                                message=f"URL not accessible: {url}",
                                severity="warning",
                            ))
                        elif not url_result.data.get("type_matches"):
                            issues.append(ValidationIssue(
                                field=f"{proj_prefix}.links[{j}]",
                                message=f"URL type mismatch: expected {link_type}, detected {url_result.data.get('detected_type')}",
                                severity="info",
                            ))

            # Infer skills from technologies
            if proj.technologies:
                skills_result = await self.call_tool(
                    "infer_skills_from_technologies",
                    {"technologies": proj.technologies},
                    context,
                )
                if skills_result.is_success and skills_result.data:
                    # Store inferred domains in metadata for later use
                    context.metadata[f"project_{i}_domains"] = skills_result.data.get(
                        "inferred_domains", []
                    )

            # Validate bullets
            for j, bullet in enumerate(proj.bullets):
                improvement_result = await self.call_tool(
                    "suggest_improvements",
                    {
                        "bullet": bullet.content,
                        "context": f"Project: {proj.name}",
                    },
                    context,
                )
                if improvement_result.is_success and improvement_result.data:
                    score = improvement_result.data.get("score", 100)
                    if score < 50:
                        issues.append(ValidationIssue(
                            field=f"{proj_prefix}.bullets[{j}]",
                            message=f"Bullet quality score: {score}/100",
                            severity="warning",
                            suggestion="; ".join(
                                s["message"]
                                for s in improvement_result.data.get("suggestions", [])
                            ),
                        ))

            # Check for GitHub enrichment opportunity
            github_link = next(
                (l for l in proj.links if l.get("type") == "github"),
                None,
            )
            if github_link:
                context.metadata[f"project_{i}_github"] = github_link.get("url")

        return issues

    async def refine(
        self,
        data: ProjectExtractionResult,
        issues: list[ValidationIssue],
        context: AgentContext,
    ) -> ProjectExtractionResult:
        """Refine extraction based on validation issues.

        Removes invalid URLs and updates data based on enrichment.
        """
        # Collect indices of links to remove
        invalid_links: dict[int, set[int]] = {}  # project_idx -> set of link indices

        for issue in issues:
            if "Invalid URL" in issue.message and issue.severity == "error":
                try:
                    # Parse field like "projects[0].links[1]"
                    parts = issue.field.split(".")
                    proj_idx = int(parts[0].split("[")[1].split("]")[0])
                    link_idx = int(parts[1].split("[")[1].split("]")[0])

                    if proj_idx not in invalid_links:
                        invalid_links[proj_idx] = set()
                    invalid_links[proj_idx].add(link_idx)
                except (IndexError, ValueError):
                    pass

        # Filter out invalid links
        if invalid_links:
            for proj_idx, link_indices in invalid_links.items():
                if proj_idx < len(data.projects):
                    proj = data.projects[proj_idx]
                    proj.links = [
                        link for i, link in enumerate(proj.links)
                        if i not in link_indices
                    ]
            logger.info(f"Removed {sum(len(v) for v in invalid_links.values())} invalid links")

        return data
