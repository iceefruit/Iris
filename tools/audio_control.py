"""Windows Master Audio & Volume Control Tool for Iris."""

import subprocess
from typing import Any, Dict, Optional
import pyautogui

from tools.base import BaseTool, ToolResult


class AudioControlTool(BaseTool):
    """Controls Windows master audio volume, mute state, and step adjustments."""

    @property
    def name(self) -> str:
        return "control_volume"

    @property
    def description(self) -> str:
        return (
            "Controls Windows master audio volume and mute settings. "
            "Use this when asked to change volume (e.g., 'set volume to 50%', 'turn volume up', 'mute audio')."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["set", "up", "down", "mute", "unmute", "toggle_mute"],
                    "description": "Volume action to perform.",
                },
                "level": {
                    "type": "integer",
                    "description": "Target volume percentage (0 to 100) when action is 'set'.",
                },
                "steps": {
                    "type": "integer",
                    "description": "Number of step increments (each ~2%) for 'up' or 'down' actions (default: 5).",
                },
            },
            "required": ["action"],
        }

    def execute(
        self,
        action: str,
        level: Optional[int] = None,
        steps: int = 5,
    ) -> ToolResult:
        act = action.lower().strip()
        step_count = max(1, min(50, steps))

        if act in ("mute", "unmute", "toggle_mute"):
            pyautogui.press("volumemute")
            return ToolResult(
                success=True,
                output=f"Toggled master audio mute state ({act}).",
            )

        if act == "up":
            for _ in range(step_count):
                pyautogui.press("volumeup")
            return ToolResult(
                success=True,
                output=f"Increased volume by {step_count * 2}% ({step_count} steps).",
            )

        if act == "down":
            for _ in range(step_count):
                pyautogui.press("volumedown")
            return ToolResult(
                success=True,
                output=f"Decreased volume by {step_count * 2}% ({step_count} steps).",
            )

        if act == "set":
            if level is None:
                return ToolResult(
                    success=False,
                    output="",
                    error="Action 'set' requires the 'level' parameter (0-100).",
                )
            target = max(0, min(100, int(level)))

            # Attempt PowerShell NirCmd-free script to set volume precisely if possible, or key stepping
            ps_script = (
                "$w = New-Object -ComObject WScript.Shell; "
                "1..50 | ForEach-Object { $w.SendKeys([char]174) }; "  # Mute/lower to 0
                f"1..{target // 2} | ForEach-Object {{ $w.SendKeys([char]175) }};"  # Raise to target
            )
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    capture_output=True,
                    timeout=3.0,
                )
                return ToolResult(
                    success=True,
                    output=f"Master volume set to approximately {target}%.",
                )
            except Exception:
                # Fallback to key stepping
                for _ in range(50):
                    pyautogui.press("volumedown")
                for _ in range(target // 2):
                    pyautogui.press("volumeup")
                return ToolResult(
                    success=True,
                    output=f"Master volume adjusted to {target}%.",
                )

        return ToolResult(
            success=False,
            output="",
            error=f"Unknown volume action: '{action}'.",
        )
