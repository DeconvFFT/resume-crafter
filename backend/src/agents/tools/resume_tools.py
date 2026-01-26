"""Tools for resume generation agents.

These tools provide specialized functionality for:
- Scoring bullet relevance
- Checking ATS compatibility
"""

import re
from typing import Any

from .registry import Tool, ToolParameter, ToolResult, ToolStatus


def score_bullet_relevance(
    bullet_content: str,
    requirements: list[dict],
) -> ToolResult:
    """Score how relevant a bullet point is to job requirements.

    Uses keyword matching and heuristics for fast scoring.
    For LLM-based scoring, use the MappingAgent directly.

    Args:
        bullet_content: The bullet point text to score.
        requirements: List of job requirements with content and keywords.

    Returns:
        ToolResult with relevance score and matched requirements.
    """
    if not bullet_content or not requirements:
        return ToolResult(
            status=ToolStatus.SUCCESS,
            data={
                "relevance_score": 0.0,
                "matched_indices": [],
                "explanation": "Empty input",
            },
        )

    bullet_lower = bullet_content.lower()
    bullet_words = set(re.findall(r'\b\w+\b', bullet_lower))

    matched_indices = []
    total_score = 0.0

    for i, req in enumerate(requirements):
        req_content = req.get("content", "").lower()
        req_keywords = [k.lower() for k in req.get("keywords", [])]
        importance = req.get("importance_score", 3)

        # Check keyword matches
        keyword_matches = sum(1 for k in req_keywords if k in bullet_lower)
        keyword_score = keyword_matches / len(req_keywords) if req_keywords else 0

        # Check content word overlap
        req_words = set(re.findall(r'\b\w+\b', req_content))
        common_words = bullet_words & req_words
        # Exclude common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "is", "are", "was", "were"}
        common_words -= stop_words
        overlap_score = len(common_words) / max(len(req_words - stop_words), 1)

        # Combined score (weighted by importance)
        req_score = (keyword_score * 0.7 + overlap_score * 0.3) * (importance / 5)

        if req_score > 0.3:
            matched_indices.append(i)
            total_score += req_score

    # Normalize score
    relevance_score = min(total_score / len(requirements), 1.0) if requirements else 0.0

    return ToolResult(
        status=ToolStatus.SUCCESS,
        data={
            "relevance_score": relevance_score,
            "matched_indices": matched_indices,
            "explanation": f"Matched {len(matched_indices)} requirements via keyword analysis",
        },
    )


def check_ats_compatibility(resume_content: str) -> ToolResult:
    """Check if resume content is ATS-friendly.

    Analyzes the resume for common ATS compatibility issues.

    Args:
        resume_content: Resume text to analyze (markdown or plain text).

    Returns:
        ToolResult with ATS score, issues, and suggestions.
    """
    if not resume_content:
        return ToolResult(
            status=ToolStatus.ERROR,
            error="Empty resume content",
        )

    score = 100.0
    issues = []
    suggestions = []

    # Check for standard section headers
    standard_headers = {
        "experience", "work experience", "professional experience",
        "skills", "technical skills",
        "education", "projects", "publications",
        "summary", "professional summary", "objective",
    }

    found_headers = set()
    lines = resume_content.lower().split("\n")
    for line in lines:
        line_clean = line.strip("#").strip("*").strip().strip(":")
        if line_clean in standard_headers:
            found_headers.add(line_clean)

    if not found_headers:
        score -= 15
        issues.append("No standard section headers found")
        suggestions.append("Use standard headers like EXPERIENCE, SKILLS, EDUCATION")

    # Check for contact info
    has_email = "@" in resume_content and "." in resume_content
    has_phone = bool(re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', resume_content))

    if not has_email:
        score -= 10
        issues.append("No email address detected")

    if not has_phone:
        score -= 5
        issues.append("No phone number detected")

    # Check for bullet points
    bullet_count = resume_content.count("•") + resume_content.count("-")
    if bullet_count < 5:
        score -= 10
        suggestions.append("Add more bullet points to describe achievements")

    # Check for action verbs at start of bullets
    action_verbs = {
        "developed", "implemented", "designed", "managed", "led", "created",
        "built", "launched", "improved", "increased", "decreased", "achieved",
        "delivered", "optimized", "automated", "integrated", "analyzed",
        "collaborated", "coordinated", "established", "executed", "generated",
        "drove", "spearheaded", "streamlined", "enhanced", "reduced",
    }

    bullet_lines = [l.strip().lstrip("•-").strip() for l in lines if l.strip().startswith(("•", "-"))]
    action_verb_bullets = 0
    for bullet in bullet_lines:
        first_word = bullet.split()[0].lower() if bullet.split() else ""
        if first_word in action_verbs:
            action_verb_bullets += 1

    if bullet_lines:
        action_ratio = action_verb_bullets / len(bullet_lines)
        if action_ratio < 0.5:
            score -= 10
            suggestions.append("Start bullet points with strong action verbs")

    # Check for metrics/quantification
    has_numbers = bool(re.search(r'\d+%|\$\d+|\d+\+', resume_content))
    if not has_numbers:
        score -= 10
        suggestions.append("Add quantifiable achievements (e.g., 'increased sales by 25%')")

    # Check for problematic formatting
    if "[" in resume_content and "](" in resume_content:
        # Has markdown links - OK for markdown but may not parse in some systems
        suggestions.append("Consider using plain text URLs for maximum ATS compatibility")

    # Check length (rough word count)
    word_count = len(resume_content.split())
    if word_count < 200:
        score -= 10
        issues.append("Resume appears too short")
    elif word_count > 1500:
        score -= 5
        suggestions.append("Consider condensing - most ATS prefer 1-2 pages")

    return ToolResult(
        status=ToolStatus.SUCCESS,
        data={
            "ats_score": max(score, 0),
            "issues": issues,
            "suggestions": suggestions,
            "word_count": word_count,
            "bullet_count": bullet_count,
            "has_email": has_email,
            "has_phone": has_phone,
            "sections_found": list(found_headers),
        },
    )


def register_resume_tools(registry: Any) -> None:
    """Register resume generation tools with the registry.

    Args:
        registry: ToolRegistry instance to register with.
    """
    registry.register(
        Tool(
            name="score_bullet_relevance",
            description="Score how relevant a bullet point is to job requirements",
            handler=score_bullet_relevance,
            parameters=[
                ToolParameter(
                    name="bullet_content",
                    type="string",
                    description="The bullet point text to score",
                    required=True,
                ),
                ToolParameter(
                    name="requirements",
                    type="array",
                    description="List of job requirements with content and keywords",
                    required=True,
                ),
            ],
        )
    )

    registry.register(
        Tool(
            name="check_ats_compatibility",
            description="Check if resume content is ATS-friendly",
            handler=check_ats_compatibility,
            parameters=[
                ToolParameter(
                    name="resume_content",
                    type="string",
                    description="Resume text to analyze",
                    required=True,
                ),
            ],
        )
    )
