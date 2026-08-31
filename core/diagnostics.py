"""System Diagnostics, Developer Tool Discovery, and Shell Error Analyzer."""

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ToolStatus:
    name: str
    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None


class SystemDiagnostics:
    """Discovers installed developer tools, CLI runtimes, and analyzes environment health."""

    COMMON_DEV_TOOLS = [
        ("git", ["git", "--version"]),
        ("python", [sys.executable, "--version"]),
        ("node", ["node", "--version"]),
        ("npm", ["npm", "--version"]),
        ("pnpm", ["pnpm", "--version"]),
        ("yarn", ["yarn", "--version"]),
        ("docker", ["docker", "--version"]),
        ("rustc", ["rustc", "--version"]),
        ("cargo", ["cargo", "--version"]),
        ("go", ["go", "version"]),
        ("powershell", ["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"]),
        ("wsl", ["wsl", "--status"]),
        ("ffmpeg", ["ffmpeg", "-version"]),
    ]

    @classmethod
    def check_tool(cls, name: str, cmd: List[str]) -> ToolStatus:
        tool_exe = shutil.which(cmd[0])
        if not tool_exe and not os.path.exists(cmd[0]):
            return ToolStatus(name=name, installed=False)

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2.0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            version_output = (res.stdout or res.stderr).strip().splitlines()
            ver_str = version_output[0] if version_output else "Installed"
            return ToolStatus(
                name=name,
                installed=True,
                version=ver_str[:60],
                path=tool_exe or cmd[0],
            )
        except Exception:
            return ToolStatus(name=name, installed=True, version="Installed (Version probe timeout)", path=tool_exe)

    @classmethod
    def run_full_diagnostics(cls) -> Dict[str, Any]:
        """Runs complete developer environment inspection."""
        tools_report = []
        for name, cmd in cls.COMMON_DEV_TOOLS:
            tools_report.append(cls.check_tool(name, cmd))

        return {
            "os": f"{platform.system()} {platform.release()} ({platform.version()})",
            "architecture": platform.machine(),
            "python_runtime": f"Python {platform.python_version()} ({sys.executable})",
            "cwd": os.getcwd(),
            "tools": tools_report,
        }

    @classmethod
    def analyze_shell_error(cls, command: str, returncode: int, stderr: str) -> str:
        """Analyzes a failed command execution and suggests fixes."""
        lower_err = stderr.lower()
        if "is not recognized as an internal or external command" in lower_err or "command not found" in lower_err:
            return "The requested CLI executable was not found on PATH. Verify installation or install via winget / scoop."
        elif "execution of scripts is disabled on this system" in lower_err:
            return "PowerShell ExecutionPolicy restriction. Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`."
        elif "permission denied" in lower_err or "access is denied" in lower_err:
            return "Administrative permissions required. Try running PowerShell as Administrator."
        elif "no space left on device" in lower_err:
            return "Disk space is exhausted on target drive."
        else:
            return f"Command exited with status code {returncode}."
