"""Sandboxed file operations.

Both tools confine every path to a configured sandbox root. Paths are resolved
and checked so an agent cannot escape the sandbox via ``..`` traversal or
absolute paths — a critical guardrail when an autonomous loop is writing files
on behalf of an SME.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from tools.base import Tool, ToolError


class _Sandbox:
    """Mixin providing safe path resolution within a root directory."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        # `is_relative_to` (py3.9+) guarantees we stayed inside the sandbox.
        if not candidate.is_relative_to(self.root):
            raise ToolError(f"Path escapes sandbox: {relative_path!r} resolved outside {self.root}")
        return candidate


class ReadFileArgs(BaseModel):
    path: str = Field(description="Path relative to the sandbox root.")
    max_bytes: int = Field(default=100_000, ge=1, le=5_000_000)


class WriteFileArgs(BaseModel):
    path: str = Field(description="Path relative to the sandbox root.")
    content: str = Field(description="UTF-8 text content to write.")
    append: bool = Field(default=False, description="Append instead of overwrite.")


class ReadFileTool(_Sandbox, Tool):
    name = "read_file"
    description = "Read a UTF-8 text file located inside the sandbox workspace."
    args_schema = ReadFileArgs

    def run(self, path: str, max_bytes: int = 100_000) -> str:  # type: ignore[override]
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"File not found: {path!r}")
        data = target.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace")


class WriteFileTool(_Sandbox, Tool):
    name = "write_file"
    description = "Create or update a UTF-8 text file inside the sandbox workspace."
    args_schema = WriteFileArgs

    def run(self, path: str, content: str, append: bool = False) -> str:  # type: ignore[override]
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with target.open(mode, encoding="utf-8") as handle:
            handle.write(content)
        return f"Wrote {len(content)} chars to {path!r}"
