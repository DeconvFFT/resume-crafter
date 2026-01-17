"""Enrichment tools for fetching external data.

Provides tools for GitHub repo data, web content, etc.
"""

import logging
from typing import Any

from .registry import ToolRegistry, ToolParameter, ToolResult, ToolStatus

logger = logging.getLogger(__name__)


def register_enrichment_tools(registry: ToolRegistry) -> None:
    """Register enrichment tools with the registry."""

    @registry.register(
        name="github_fetch",
        description="Fetch repository information from GitHub",
        parameters=[
            ToolParameter(
                name="url",
                type="string",
                description="GitHub repository URL (e.g., https://github.com/owner/repo)",
            ),
        ],
    )
    async def github_fetch(url: str) -> ToolResult:
        """Fetch GitHub repository information."""
        try:
            from src.integrations.github import GitHubService

            # Parse GitHub URL
            parsed = GitHubService.parse_github_url(url)
            if not parsed:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Invalid GitHub URL: {url}",
                )

            owner, repo = parsed
            github = GitHubService()

            # Fetch comprehensive repo info
            repo_info = await github.get_comprehensive_repo_info(owner, repo)

            if not repo_info:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Failed to fetch repository: {owner}/{repo}",
                )

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "owner": owner,
                    "repo": repo,
                    "url": url,
                    "info": repo_info,
                },
            )

        except Exception as e:
            logger.exception(f"GitHub fetch failed: {e}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=f"GitHub fetch failed: {e}",
            )

    @registry.register(
        name="infer_skills_from_technologies",
        description="Infer additional skills and categorize technologies",
        parameters=[
            ToolParameter(
                name="technologies",
                type="array",
                description="List of technologies/tools mentioned",
            ),
        ],
    )
    async def infer_skills_from_technologies(technologies: list[str]) -> ToolResult:
        """Infer skills and categories from a list of technologies."""
        # Technology to category mapping
        tech_categories = {
            # Programming Languages
            "python": ("programming_language", ["data science", "backend", "scripting"]),
            "javascript": ("programming_language", ["frontend", "backend", "web"]),
            "typescript": ("programming_language", ["frontend", "backend", "web"]),
            "java": ("programming_language", ["backend", "enterprise", "android"]),
            "go": ("programming_language", ["backend", "systems", "cloud"]),
            "rust": ("programming_language", ["systems", "performance"]),
            "c++": ("programming_language", ["systems", "performance", "games"]),
            "c": ("programming_language", ["systems", "embedded"]),
            "ruby": ("programming_language", ["backend", "scripting"]),
            "php": ("programming_language", ["backend", "web"]),
            "swift": ("programming_language", ["ios", "mobile"]),
            "kotlin": ("programming_language", ["android", "backend"]),

            # Frameworks
            "react": ("framework", ["frontend", "web"]),
            "vue": ("framework", ["frontend", "web"]),
            "angular": ("framework", ["frontend", "web"]),
            "django": ("framework", ["backend", "web"]),
            "flask": ("framework", ["backend", "web"]),
            "fastapi": ("framework", ["backend", "api"]),
            "express": ("framework", ["backend", "web"]),
            "spring": ("framework", ["backend", "enterprise"]),
            "rails": ("framework", ["backend", "web"]),
            "nextjs": ("framework", ["fullstack", "web"]),
            "nestjs": ("framework", ["backend", "web"]),

            # Databases
            "postgresql": ("database", ["sql", "relational"]),
            "mysql": ("database", ["sql", "relational"]),
            "mongodb": ("database", ["nosql", "document"]),
            "redis": ("database", ["cache", "nosql"]),
            "elasticsearch": ("database", ["search", "nosql"]),
            "sqlite": ("database", ["sql", "embedded"]),

            # Cloud
            "aws": ("cloud", ["infrastructure", "deployment"]),
            "gcp": ("cloud", ["infrastructure", "deployment"]),
            "azure": ("cloud", ["infrastructure", "deployment"]),
            "vercel": ("cloud", ["deployment", "frontend"]),
            "heroku": ("cloud", ["deployment", "paas"]),

            # DevOps
            "docker": ("devops", ["containerization", "deployment"]),
            "kubernetes": ("devops", ["orchestration", "infrastructure"]),
            "terraform": ("devops", ["iac", "infrastructure"]),
            "jenkins": ("devops", ["ci/cd", "automation"]),
            "github actions": ("devops", ["ci/cd", "automation"]),
            "gitlab ci": ("devops", ["ci/cd", "automation"]),

            # AI/ML
            "tensorflow": ("tool", ["machine learning", "deep learning"]),
            "pytorch": ("tool", ["machine learning", "deep learning"]),
            "scikit-learn": ("tool", ["machine learning", "data science"]),
            "pandas": ("tool", ["data analysis", "data science"]),
            "numpy": ("tool", ["data analysis", "scientific computing"]),
            "langchain": ("tool", ["ai", "llm"]),
            "openai": ("tool", ["ai", "llm"]),
        }

        categorized = []
        inferred_domains = set()

        for tech in technologies:
            tech_lower = tech.lower().strip()

            if tech_lower in tech_categories:
                category, domains = tech_categories[tech_lower]
                categorized.append({
                    "name": tech,
                    "category": category,
                    "related_domains": domains,
                })
                inferred_domains.update(domains)
            else:
                # Unknown technology
                categorized.append({
                    "name": tech,
                    "category": "other",
                    "related_domains": [],
                })

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "technologies": categorized,
                "inferred_domains": list(inferred_domains),
                "total_categorized": len([t for t in categorized if t["category"] != "other"]),
            },
        )

    @registry.register(
        name="suggest_improvements",
        description="Suggest improvements for a bullet point",
        parameters=[
            ToolParameter(
                name="bullet",
                type="string",
                description="The bullet point text to improve",
            ),
            ToolParameter(
                name="context",
                type="string",
                description="Additional context (job title, company, project type)",
                required=False,
            ),
        ],
    )
    async def suggest_improvements(bullet: str, context: str | None = None) -> ToolResult:
        """Analyze a bullet point and suggest improvements."""
        suggestions = []
        score = 100

        # Check for action verb at start
        action_verbs = [
            "developed", "built", "created", "designed", "implemented", "led",
            "managed", "improved", "increased", "reduced", "achieved", "launched",
            "automated", "optimized", "architected", "deployed", "maintained",
            "collaborated", "integrated", "analyzed", "established", "streamlined",
        ]

        first_word = bullet.split()[0].lower() if bullet else ""
        if first_word not in action_verbs:
            suggestions.append({
                "type": "action_verb",
                "message": "Start with a strong action verb (e.g., 'Developed', 'Led', 'Implemented')",
                "severity": "high",
            })
            score -= 20

        # Check for metrics/quantification
        import re
        has_metrics = bool(re.search(r'\d+%|\d+x|\$[\d,]+|\d+\+?\s*(users|customers|requests|transactions|projects|team)', bullet.lower()))
        if not has_metrics:
            suggestions.append({
                "type": "metrics",
                "message": "Add quantifiable results (e.g., 'increased performance by 40%', 'served 10K+ users')",
                "severity": "high",
            })
            score -= 15

        # Check length
        word_count = len(bullet.split())
        if word_count < 10:
            suggestions.append({
                "type": "length",
                "message": "Bullet is too brief. Add more context about impact and technologies used.",
                "severity": "medium",
            })
            score -= 10
        elif word_count > 40:
            suggestions.append({
                "type": "length",
                "message": "Bullet is too long. Keep it concise (under 2 lines).",
                "severity": "medium",
            })
            score -= 10

        # Check for vague language
        vague_words = ["helped", "assisted", "worked on", "was responsible for", "involved in"]
        if any(vw in bullet.lower() for vw in vague_words):
            suggestions.append({
                "type": "specificity",
                "message": "Replace vague language ('helped', 'worked on') with specific contributions",
                "severity": "high",
            })
            score -= 15

        # Check for technologies mentioned
        tech_pattern = r'\b(Python|Java|JavaScript|TypeScript|React|Vue|Angular|Node|Django|Flask|FastAPI|AWS|GCP|Azure|Docker|Kubernetes|PostgreSQL|MongoDB|Redis)\b'
        has_tech = bool(re.search(tech_pattern, bullet, re.IGNORECASE))
        if not has_tech:
            suggestions.append({
                "type": "technologies",
                "message": "Consider mentioning specific technologies used",
                "severity": "low",
            })
            score -= 5

        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "original": bullet,
                "score": max(0, score),
                "suggestions": suggestions,
                "has_action_verb": first_word in action_verbs,
                "has_metrics": has_metrics,
                "word_count": word_count,
            },
        )
