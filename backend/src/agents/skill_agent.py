"""Skill extraction agent with categorization and deduplication.

Extracts skills from documents with:
- Category inference
- Proficiency estimation
- Duplicate detection
"""

import logging
from typing import Any

from src.models.schemas.llm_outputs import SkillExtractionResult

from .base import BaseAgent, AgentContext, ValidationIssue

logger = logging.getLogger(__name__)


class SkillAgent(BaseAgent[SkillExtractionResult]):
    """Agent for extracting and validating skills."""

    def __init__(self, llm_client: Any = None):
        super().__init__(
            name="SkillAgent",
            description="Extracts skills with categorization",
            llm_client=llm_client,
        )

    async def extract(self, context: AgentContext) -> SkillExtractionResult | None:
        """Extract skills from document."""
        if not self._llm:
            raise ValueError("LLM client not set")

        logger.info(f"Extracting skills from document {context.document_id}")
        result = await self._llm.extract_skills(context.document_text)

        # Debug logging
        if result and result.skills:
            logger.info(f"SkillAgent extracted {len(result.skills)} skills: {[s.name for s in result.skills[:5]]}...")
        else:
            logger.warning(f"SkillAgent extracted 0 skills or None result: {result}")

        return result

    async def validate(
        self,
        data: SkillExtractionResult,
        context: AgentContext,
    ) -> list[ValidationIssue]:
        """Validate extracted skills."""
        issues = []
        seen_skills = set()

        for i, skill in enumerate(data.skills):
            skill_prefix = f"skills[{i}]"
            skill_lower = skill.name.lower().strip()

            # Check for duplicates within this extraction
            if skill_lower in seen_skills:
                issues.append(ValidationIssue(
                    field=skill_prefix,
                    message=f"Duplicate skill: {skill.name}",
                    severity="error",
                ))
            else:
                seen_skills.add(skill_lower)

            # Verify category makes sense
            tech_result = await self.call_tool(
                "infer_skills_from_technologies",
                {"technologies": [skill.name]},
                context,
            )
            if tech_result.is_success and tech_result.data:
                categorized = tech_result.data.get("technologies", [])
                if categorized and categorized[0].get("category") != "other":
                    inferred_category = categorized[0]["category"]
                    if skill.category.lower() != inferred_category:
                        issues.append(ValidationIssue(
                            field=f"{skill_prefix}.category",
                            message=f"Category mismatch: extracted '{skill.category}', expected '{inferred_category}'",
                            severity="info",
                            suggestion=f"Consider using category: {inferred_category}",
                        ))

            # Check for overly vague skills
            vague_skills = [
                "programming", "coding", "development", "software",
                "technology", "computers", "technical", "it",
            ]
            if skill_lower in vague_skills:
                issues.append(ValidationIssue(
                    field=skill_prefix,
                    message=f"Skill '{skill.name}' is too vague",
                    severity="warning",
                    suggestion="Use specific technologies or methodologies instead",
                ))

        return issues

    async def refine(
        self,
        data: SkillExtractionResult,
        issues: list[ValidationIssue],
        context: AgentContext,
    ) -> SkillExtractionResult:
        """Refine extraction by removing duplicates and vague skills."""
        # Find indices to remove
        indices_to_remove = set()

        for issue in issues:
            if issue.severity == "error" and "Duplicate" in issue.message:
                try:
                    idx = int(issue.field.split("[")[1].split("]")[0])
                    indices_to_remove.add(idx)
                except (IndexError, ValueError):
                    pass

        # Filter out duplicates
        if indices_to_remove:
            filtered_skills = [
                skill for i, skill in enumerate(data.skills)
                if i not in indices_to_remove
            ]
            logger.info(f"Removed {len(indices_to_remove)} duplicate skills")
            return SkillExtractionResult(skills=filtered_skills)

        return data
