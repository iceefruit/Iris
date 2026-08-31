"""Windows Application and Process Launcher Tool."""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from tools.base import BaseTool, ToolResult


class LaunchAppTool(BaseTool):
    """Launches desktop applications by executable name, URI, or Start Menu shortcut."""

    name = "launch_application"
    description = (
        "Launches a Windows application, utility, or protocol URI. "
        "Examples: 'notepad', 'chrome', 'spotify', 'code', 'calc', 'ms-settings:'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "app_name": {
                "type": "string",
                "description": "Name of the app, executable, URI protocol, or command to launch (e.g. 'notepad', 'calc:', 'chrome', 'code').",
            },
            "arguments": {
                "type": "string",
                "default": "",
                "description": "Optional CLI arguments or target file path to pass to the application.",
            },
        },
        "required": ["app_name"],
    }

    def _find_start_menu_shortcut(self, target_name: str) -> List[Path]:
        """Scans User and System Start Menu directories for matching shortcuts."""
        search_dirs = [
            Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("ProgramData", "")) / r"Microsoft\Windows\Start Menu\Programs",
        ]
        matches = []
        target_lower = target_name.lower()
        for sdir in search_dirs:
            if sdir.exists():
                for p in sdir.rglob("*.lnk"):
                    if target_lower in p.stem.lower():
                        matches.append(p)
        return matches

    def execute(self, app_name: str, arguments: str = "", **kwargs) -> ToolResult:
        app_clean = app_name.strip()
        if not app_clean:
            return ToolResult(success=False, output="", error="Application name cannot be empty.")

        # 1. Check URI Protocol (e.g., ms-settings:, calc:, spotify:)
        if ":" in app_clean and not app_clean.startswith("\\") and len(app_clean.split(":")[0]) > 1:
            try:
                os.startfile(app_clean)
                return ToolResult(success=True, output=f"Dispatched Windows URI: {app_clean}")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Failed to open URI: {e}")

        # 2. Check Start Menu Shortcuts
        shortcuts = self._find_start_menu_shortcut(app_clean)
        if shortcuts:
            try:
                os.startfile(str(shortcuts[0]))
                return ToolResult(success=True, output=f"Launched application shortcut: '{shortcuts[0].stem}'")
            except Exception as e:
                pass

        # 3. Direct process spawn via Windows Shell / PowerShell
        try:
            cmd = f'Start-Process -FilePath "{app_clean}"'
            if arguments:
                cmd += f' -ArgumentList "{arguments}"'
            
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0:
                return ToolResult(success=True, output=f"Launched '{app_clean}' successfully.")
            else:
                err = res.stderr.strip() or res.stdout.strip()
                # Fallback to os.startfile
                try:
                    os.startfile(app_clean)
                    return ToolResult(success=True, output=f"Launched '{app_clean}' via shell.")
                except Exception:
                    return ToolResult(success=False, output="", error=err or f"Failed to start {app_clean}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Launch failed: {str(e)}")
