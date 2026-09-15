"""Tool abstraction and registry.

Every tool exposes a ``name``, a human/LLM-readable ``description``, and a
Pydantic schema describing its arguments. The registry validates arguments
before dispatch, which turns malformed model output into a clean, recoverable
error rather than a runtime crash.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError


class ToolError(Exception):
    """Raised when a tool cannot complete an action safely or successfully."""


class Tool(ABC):
    """Base class for all tools."""

    name: str
    description: str
    args_schema: type[BaseModel]

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the tool with already-validated arguments."""
        raise NotImplementedError

    def invoke(self, arguments: dict[str, Any]) -> Any:
        """Validate ``arguments`` against the schema, then run the tool."""
        try:
            validated = self.args_schema(**arguments)
        except ValidationError as exc:
            raise ToolError(f"Invalid arguments for tool {self.name!r}: {exc}") from exc
        return self.run(**validated.model_dump())

    def spec(self) -> dict[str, Any]:
        """Return a JSON-serialisable description for prompting the LLM."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.args_schema.model_json_schema(),
        }


class ToolRegistry:
    """Holds the set of tools available to an agent and dispatches calls."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolError(f"Unknown tool: {name!r}. Available: {sorted(self._tools)}")
        return self._tools[name]

    def dispatch(self, name: str, arguments: dict[str, Any]) -> Any:
        return self.get(name).invoke(arguments)

    def specs(self) -> list[dict[str, Any]]:
        return [tool.spec() for tool in self._tools.values()]

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


def build_default_registry(settings: Any = None) -> ToolRegistry:
    """Assemble the standard SME toolset from configuration."""
    from core.config import get_settings
    from tools.db_queries import DatabaseQueryTool
    from tools.file_ops import ReadFileTool, WriteFileTool

    settings = settings or get_settings()
    return ToolRegistry(
        [
            ReadFileTool(settings.sandbox_root),
            WriteFileTool(settings.sandbox_root),
            DatabaseQueryTool(settings.database_url),
        ]
    )
