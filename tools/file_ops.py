"""File and Directory Management Tool with Safe Recycle Bin Deletion."""

import os
from pathlib import Path
from typing import Dict, Any, List
from send2trash import send2trash
from tools.base import BaseTool, ToolResult


class FileOperationTool(BaseTool):
    """Performs filesystem inspection, reading, writing, and safe deletion."""

    name = "file_operation"
    description = (
        "Performs filesystem operations: 'read', 'write', 'append', 'list_dir', 'search', or 'delete'. "
        "Deletions are safely sent to the Windows Recycle Bin via send2trash."
    )
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "append", "list_dir", "search", "delete"],
                "description": "The file operation to perform.",
            },
            "path": {
                "type": "string",
                "description": "Absolute or relative filesystem path.",
            },
            "content": {
                "type": "string",
                "description": "Content string for 'write' or 'append' operations.",
            },
            "pattern": {
                "type": "string",
                "default": "*",
                "description": "Search glob pattern for 'search' or 'list_dir' (e.g. '*.py').",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional 1-indexed start line for 'read'.",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional 1-indexed end line for 'read'.",
            },
        },
        "required": ["operation", "path"],
    }

    def execute(
        self,
        operation: str,
        path: str,
        content: str = "",
        pattern: str = "*",
        start_line: int = 1,
        end_line: int = 500,
        **kwargs,
    ) -> ToolResult:
        target = Path(path).expanduser().resolve()

        try:
            if operation == "read":
                if not target.exists() or not target.is_file():
                    return ToolResult(success=False, output="", error=f"File not found: {target}")
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                slice_lines = lines[max(0, start_line - 1):end_line]
                numbered = [f"{i + start_line}: {line}" for i, line in enumerate(slice_lines)]
                return ToolResult(success=True, output="".join(numbered) or "(File is empty)")

            elif operation == "write":
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(content)
                return ToolResult(success=True, output=f"Successfully wrote {len(content)} bytes to {target}")

            elif operation == "append":
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "a", encoding="utf-8") as f:
                    f.write(content)
                return ToolResult(success=True, output=f"Appended {len(content)} bytes to {target}")

            elif operation == "list_dir":
                if not target.exists() or not target.is_dir():
                    return ToolResult(success=False, output="", error=f"Directory not found: {target}")
                entries = []
                for item in sorted(target.iterdir()):
                    kind = "[DIR]" if item.is_dir() else f"[{item.stat().st_size} B]"
                    entries.append(f"{kind.ljust(12)} {item.name}")
                return ToolResult(success=True, output="\n".join(entries) or "(Empty directory)")

            elif operation == "search":
                if not target.exists() or not target.is_dir():
                    return ToolResult(success=False, output="", error=f"Directory not found: {target}")
                matches = [str(p.relative_to(target)) for p in target.rglob(pattern)][:100]
                return ToolResult(success=True, output="\n".join(matches) or f"No files matching '{pattern}'")

            elif operation == "delete":
                if not target.exists():
                    return ToolResult(success=False, output="", error=f"Target path does not exist: {target}")
                send2trash(str(target))
                return ToolResult(success=True, output=f"Safely recycled to Windows Trash: {target}")

            else:
                return ToolResult(success=False, output="", error=f"Unsupported operation: {operation}")

        except Exception as e:
            return ToolResult(success=False, output="", error=f"File operation failed: {str(e)}")
