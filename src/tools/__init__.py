"""Agent-computer interfaces (ACI) and sandboxed actions.

Tools are the *only* way an agent affects the outside world. Each tool is a
small, well-described, validated function so the model has a clear, safe
surface to act through. A ``ToolRegistry`` provides discovery and dispatch.
"""

from tools.base import Tool, ToolError, ToolRegistry, build_default_registry
from tools.db_queries import DatabaseQueryTool
from tools.file_ops import ReadFileTool, WriteFileTool

__all__ = [
    "Tool",
    "ToolError",
    "ToolRegistry",
    "build_default_registry",
    "DatabaseQueryTool",
    "ReadFileTool",
    "WriteFileTool",
]
