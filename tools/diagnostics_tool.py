"""System Diagnostics Tool for Iris."""

from typing import Dict, Any, Optional
from core.diagnostics import SystemDiagnostics
from tools.base import BaseTool, ToolResult


class DiagnoseEnvironmentTool(BaseTool):
    """Tool for diagnosing installed developer runtimes, CLI tools, and OS health."""

    name = "diagnose_environment"
    description = (
        "Inspects system PATH and detects installed developer tools and runtimes "
        "(e.g. Git, Python, Node, Docker, Rust, PowerShell, WSL, FFmpeg)."
    )
    parameters = {
        "type": "object",
        "properties": {},
    }

    def execute(self, **kwargs) -> ToolResult:
        try:
            diag = SystemDiagnostics.run_full_diagnostics()
            lines = [
                f"### System & Environment Telemetry",
                f"- **OS:** {diag['os']} ({diag['architecture']})",
                f"- **Python:** {diag['python_runtime']}",
                f"- **Working Directory:** `{diag['cwd']}`",
                "",
                "### Installed Developer Tools & Runtimes:",
            ]

            for tool in diag["tools"]:
                if tool.installed:
                    lines.append(f"- **{tool.name}:** ✔ `{tool.version}` (Path: `{tool.path}`)")
                else:
                    lines.append(f"- **{tool.name}:** ❌ Not found on PATH")

            return ToolResult(success=True, output="\n".join(lines))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Diagnostics failed: {str(e)}")
