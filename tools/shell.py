"""PowerShell and local command execution tool."""

import subprocess
from typing import Any, Dict, Optional
from tools.base import BaseTool, ToolResult


class PowerShellTool(BaseTool):
    """Tool for executing PowerShell commands locally on the desktop."""

    name = "execute_powershell"
    description = (
        "Executes a PowerShell command or script locally and returns stdout and stderr output. "
        "Use for OS queries, launching programs, inspecting directories, or automated system tasks."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The exact PowerShell command string to execute.",
            },
            "timeout_seconds": {
                "type": "integer",
                "default": 30,
                "description": "Timeout in seconds before aborting (default: 30).",
            },
        },
        "required": ["command"],
    }

    def execute(self, command: str, timeout_seconds: int = 30, **kwargs) -> ToolResult:
        if not command.strip():
            return ToolResult(success=False, output="", error="Command string is empty.")

        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            stdout = res.stdout.strip()
            stderr = res.stderr.strip()

            if res.returncode == 0:
                output = stdout or "(Command completed with no output)"
                return ToolResult(success=True, output=output)
            else:
                err_msg = stderr or stdout or f"Exited with code {res.returncode}"
                return ToolResult(success=False, output=stdout, error=err_msg)

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output="",
                error=f"Command timed out after {timeout_seconds} seconds.",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to execute command: {str(e)}",
            )
