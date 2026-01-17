"""Tool registry for agent tool-calling capabilities.

Provides a registry pattern for tools that agents can call during processing.
Tools are registered with schemas for LLM-based tool selection.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """Result status for tool execution."""

    SUCCESS = "success"
    ERROR = "error"
    NOT_FOUND = "not_found"


@dataclass
class ToolResult:
    """Result of a tool execution."""

    status: ToolStatus
    data: Any = None
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status == ToolStatus.SUCCESS


class ToolParameter(BaseModel):
    """Schema for a tool parameter."""

    name: str
    type: str
    description: str
    required: bool = True
    enum: list[str] | None = None


class Tool(BaseModel):
    """Definition of a tool that agents can call."""

    name: str
    description: str
    parameters: list[ToolParameter] = []

    # The actual function is stored separately (not serializable)
    class Config:
        arbitrary_types_allowed = True

    def to_schema(self) -> dict:
        """Convert to JSON schema format for LLM."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }


# Type for async tool functions
ToolFunction = Callable[..., Awaitable[ToolResult]]


@dataclass
class RegisteredTool:
    """A tool registered in the registry."""

    definition: Tool
    function: ToolFunction


class ToolRegistry:
    """Registry for agent tools.

    Provides registration, lookup, and execution of tools.

    Usage:
        registry = ToolRegistry()

        @registry.register(
            name="validate_url",
            description="Validate that a URL is accessible",
            parameters=[
                ToolParameter(name="url", type="string", description="URL to validate")
            ]
        )
        async def validate_url(url: str) -> ToolResult:
            # implementation
            ...

        # Get tools for LLM
        schemas = registry.get_tool_schemas()

        # Execute a tool
        result = await registry.execute("validate_url", {"url": "https://example.com"})
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: list[ToolParameter] | None = None,
    ) -> Callable[[ToolFunction], ToolFunction]:
        """Decorator to register a tool function.

        Args:
            name: Unique name for the tool.
            description: Description of what the tool does.
            parameters: List of parameter definitions.

        Returns:
            Decorator function.
        """

        def decorator(func: ToolFunction) -> ToolFunction:
            tool_def = Tool(
                name=name,
                description=description,
                parameters=parameters or [],
            )
            self._tools[name] = RegisteredTool(
                definition=tool_def,
                function=func,
            )
            logger.debug(f"Registered tool: {name}")
            return func

        return decorator

    def add_tool(self, name: str, description: str, func: ToolFunction, parameters: list[ToolParameter] | None = None) -> None:
        """Add a tool programmatically.

        Args:
            name: Unique name for the tool.
            description: Description of what the tool does.
            func: The async function to call.
            parameters: List of parameter definitions.
        """
        tool_def = Tool(
            name=name,
            description=description,
            parameters=parameters or [],
        )
        self._tools[name] = RegisteredTool(
            definition=tool_def,
            function=func,
        )
        logger.debug(f"Added tool: {name}")

    def get_tool(self, name: str) -> RegisteredTool | None:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def get_tool_schemas(self) -> list[dict]:
        """Get all tool schemas for LLM consumption."""
        return [tool.definition.to_schema() for tool in self._tools.values()]

    def get_tool_names(self) -> list[str]:
        """Get list of registered tool names."""
        return list(self._tools.keys())

    async def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool by name.

        Args:
            name: Tool name to execute.
            arguments: Arguments to pass to the tool.

        Returns:
            ToolResult with success/error status and data.
        """
        tool = self._tools.get(name)
        if not tool:
            logger.warning(f"Tool not found: {name}")
            return ToolResult(
                status=ToolStatus.NOT_FOUND,
                error=f"Tool '{name}' not found",
            )

        try:
            logger.debug(f"Executing tool: {name} with args: {arguments}")
            result = await tool.function(**arguments)
            return result
        except Exception as e:
            logger.exception(f"Tool execution failed: {name}")
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )


# Global registry instance
_default_registry: ToolRegistry | None = None


def get_default_registry() -> ToolRegistry:
    """Get or create the default tool registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolRegistry()
        # Register default tools
        _register_default_tools(_default_registry)
    return _default_registry


def _register_default_tools(registry: ToolRegistry) -> None:
    """Register the default set of tools."""
    from .validation_tools import register_validation_tools
    from .vector_tools import register_vector_tools
    from .enrichment_tools import register_enrichment_tools

    register_validation_tools(registry)
    register_vector_tools(registry)
    register_enrichment_tools(registry)
