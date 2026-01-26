"""Multi-agent orchestration for intelligent document processing.

This package provides a multi-agent system for document extraction with:
- Tool-calling capabilities for validation and enrichment
- Iterative refinement loops for quality improvement
- Supervisor pattern for orchestrating specialized agents
"""

from .base import AgentState, AgentContext, BaseAgent, AgentResult, ValidationIssue
from .experience_agent import ExperienceAgent
from .project_agent import ProjectAgent
from .skill_agent import SkillAgent
from .supervisor import Supervisor, SupervisorResult, create_supervisor
from .tools.registry import ToolRegistry
from .automation import (
    ContactDiscoveryAgent,
    ContactDiscoveryResult,
    ContactInfo,
    JobQualificationAgent,
    JobRequirements,
    QualificationResult,
    SkillMatch,
    ExperienceMatch,
    UserProfile,
    OutreachAgent,
    UserContext,
    ContactContext,
    JobContext,
    OutreachDraft,
    OutreachResult,
)

__all__ = [
    # Base
    "AgentState",
    "AgentContext",
    "AgentResult",
    "BaseAgent",
    "ValidationIssue",
    # Agents
    "ExperienceAgent",
    "ProjectAgent",
    "SkillAgent",
    # Supervisor
    "Supervisor",
    "SupervisorResult",
    "create_supervisor",
    # Tools
    "ToolRegistry",
    # Automation Agents
    "ContactDiscoveryAgent",
    "ContactDiscoveryResult",
    "ContactInfo",
    "JobQualificationAgent",
    "JobRequirements",
    "QualificationResult",
    "SkillMatch",
    "ExperienceMatch",
    "UserProfile",
    "OutreachAgent",
    "UserContext",
    "ContactContext",
    "JobContext",
    "OutreachDraft",
    "OutreachResult",
]
