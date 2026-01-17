"""Base agent infrastructure for multi-agent orchestration.

Provides the foundation for specialized extraction agents with:
- State machine for tracking agent progress
- Tool calling capabilities
- Iterative refinement support
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from .tools.registry import ToolRegistry, ToolResult, get_default_registry

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AgentState(str, Enum):
    """States in the agent processing lifecycle."""

    IDLE = "idle"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    REFINING = "refining"
    TOOL_CALLING = "tool_calling"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ValidationIssue:
    """An issue found during validation."""

    field: str
    message: str
    severity: str  # "error", "warning", "info"
    suggestion: str | None = None


@dataclass
class AgentContext:
    """Context passed to agents during processing."""

    document_id: UUID
    user_id: UUID
    document_text: str
    tool_registry: ToolRegistry = field(default_factory=get_default_registry)
    max_refinements: int = 3
    current_refinement: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def can_refine(self) -> bool:
        """Check if more refinement iterations are allowed."""
        return self.current_refinement < self.max_refinements


@dataclass
class AgentResult(Generic[T]):
    """Result from an agent's extraction."""

    state: AgentState
    data: T | None = None
    validation_issues: list[ValidationIssue] = field(default_factory=list)
    tool_calls_made: list[str] = field(default_factory=list)
    refinements_done: int = 0
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        """Check if result passed validation."""
        return (
            self.state == AgentState.COMPLETE
            and not any(issue.severity == "error" for issue in self.validation_issues)
        )


class BaseAgent(ABC, Generic[T]):
    """Base class for specialized extraction agents.

    Provides the core agent loop:
    1. Extract initial data from document
    2. Validate the extraction (may call tools)
    3. If validation fails and refinements available, refine
    4. Repeat until valid or max refinements reached

    Subclasses implement:
    - extract(): Initial extraction logic
    - validate(): Validation logic (can call tools)
    - refine(): Refinement logic based on validation feedback
    """

    def __init__(
        self,
        name: str,
        description: str,
        llm_client: Any = None,
    ):
        """Initialize the agent.

        Args:
            name: Agent name for logging.
            description: What this agent extracts.
            llm_client: LLM client for extraction (optional, can be set later).
        """
        self.name = name
        self.description = description
        self._llm = llm_client
        self._state = AgentState.IDLE
        self._tool_calls: list[str] = []

    @property
    def state(self) -> AgentState:
        """Current agent state."""
        return self._state

    def set_llm_client(self, client: Any) -> None:
        """Set the LLM client for this agent."""
        self._llm = client

    async def run(self, context: AgentContext) -> AgentResult[T]:
        """Run the agent's extraction loop.

        Args:
            context: Processing context with document and tools.

        Returns:
            AgentResult with extracted data and validation status.
        """
        self._state = AgentState.IDLE
        self._tool_calls = []

        logger.info(f"Agent '{self.name}' starting for document {context.document_id}")

        try:
            # Initial extraction
            self._state = AgentState.EXTRACTING
            extraction = await self.extract(context)

            if extraction is None:
                return AgentResult(
                    state=AgentState.ERROR,
                    error="Extraction returned no data",
                    tool_calls_made=self._tool_calls,
                )

            # Validation and refinement loop
            while True:
                self._state = AgentState.VALIDATING
                issues = await self.validate(extraction, context)

                # Check if validation passed
                error_issues = [i for i in issues if i.severity == "error"]
                if not error_issues:
                    logger.info(f"Agent '{self.name}' completed successfully")
                    self._state = AgentState.COMPLETE
                    return AgentResult(
                        state=AgentState.COMPLETE,
                        data=extraction,
                        validation_issues=issues,
                        tool_calls_made=self._tool_calls,
                        refinements_done=context.current_refinement,
                    )

                # Check if we can refine
                if not context.can_refine():
                    logger.warning(
                        f"Agent '{self.name}' reached max refinements with {len(error_issues)} errors"
                    )
                    self._state = AgentState.COMPLETE
                    return AgentResult(
                        state=AgentState.COMPLETE,
                        data=extraction,
                        validation_issues=issues,
                        tool_calls_made=self._tool_calls,
                        refinements_done=context.current_refinement,
                    )

                # Refine based on feedback
                logger.info(
                    f"Agent '{self.name}' refining (attempt {context.current_refinement + 1})"
                )
                self._state = AgentState.REFINING
                context.current_refinement += 1
                extraction = await self.refine(extraction, issues, context)

        except Exception as e:
            logger.exception(f"Agent '{self.name}' failed: {e}")
            self._state = AgentState.ERROR
            return AgentResult(
                state=AgentState.ERROR,
                error=str(e),
                tool_calls_made=self._tool_calls,
            )

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: AgentContext,
    ) -> ToolResult:
        """Call a tool from the registry.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments for the tool.
            context: Agent context with tool registry.

        Returns:
            ToolResult from the tool execution.
        """
        self._state = AgentState.TOOL_CALLING
        self._tool_calls.append(tool_name)

        logger.debug(f"Agent '{self.name}' calling tool: {tool_name}")
        result = await context.tool_registry.execute(tool_name, arguments)

        # Restore previous state
        self._state = AgentState.VALIDATING

        return result

    @abstractmethod
    async def extract(self, context: AgentContext) -> T | None:
        """Extract data from the document.

        Args:
            context: Processing context.

        Returns:
            Extracted data or None if extraction failed.
        """
        pass

    @abstractmethod
    async def validate(
        self,
        data: T,
        context: AgentContext,
    ) -> list[ValidationIssue]:
        """Validate extracted data.

        Can call tools for validation (URL checking, date validation, etc.)

        Args:
            data: Extracted data to validate.
            context: Processing context with tools.

        Returns:
            List of validation issues found.
        """
        pass

    @abstractmethod
    async def refine(
        self,
        data: T,
        issues: list[ValidationIssue],
        context: AgentContext,
    ) -> T:
        """Refine extraction based on validation feedback.

        Args:
            data: Current extracted data.
            issues: Validation issues to address.
            context: Processing context.

        Returns:
            Refined extraction.
        """
        pass


class SimpleAgent(BaseAgent[T]):
    """A simple agent that uses provided functions for extraction/validation.

    Useful for creating agents without subclassing.
    """

    def __init__(
        self,
        name: str,
        description: str,
        extract_fn,
        validate_fn=None,
        refine_fn=None,
        llm_client=None,
    ):
        super().__init__(name, description, llm_client)
        self._extract_fn = extract_fn
        self._validate_fn = validate_fn
        self._refine_fn = refine_fn

    async def extract(self, context: AgentContext) -> T | None:
        return await self._extract_fn(context, self._llm)

    async def validate(self, data: T, context: AgentContext) -> list[ValidationIssue]:
        if self._validate_fn:
            return await self._validate_fn(data, context, self)
        return []  # No validation by default

    async def refine(
        self, data: T, issues: list[ValidationIssue], context: AgentContext
    ) -> T:
        if self._refine_fn:
            return await self._refine_fn(data, issues, context, self._llm)
        return data  # No refinement by default
