"""Windows Window Management & Focus Tool for Iris."""

import ctypes
import ctypes.wintypes
from typing import Any, Dict, List, Optional, Tuple
import pyautogui

from tools.base import BaseTool, ToolResult

user32 = ctypes.windll.user32


class WindowManagerTool(BaseTool):
    """Manages application windows on Windows (focus, snap, minimize, maximize, list)."""

    @property
    def name(self) -> str:
        return "manage_window"

    @property
    def description(self) -> str:
        return (
            "Manages and manipulates desktop application windows on Windows. "
            "Supports focusing a window by title/app name, snapping windows left/right, "
            "minimizing, maximizing, restoring, and listing all open windows."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["focus", "minimize", "maximize", "restore", "snap_left", "snap_right", "list_open"],
                    "description": "Window management action to perform.",
                },
                "window_title": {
                    "type": "string",
                    "description": "Partial or full title / application name to match (e.g. 'Spotify', 'Chrome', 'Visual Studio Code', 'Discord').",
                },
            },
            "required": ["action"],
        }

    def _get_visible_windows(self) -> List[Tuple[int, str]]:
        """Returns list of visible window (hwnd, title) tuples."""
        windows = []

        def enum_handler(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()
                    if title and title not in ("Program Manager", "Default IME", "MSCTFIME UI"):
                        windows.append((hwnd, title))
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
        return windows

    def _find_hwnd(self, query: str) -> Optional[Tuple[int, str]]:
        """Finds matching window HWND by partial title search."""
        query_lower = query.lower().strip()
        visible = self._get_visible_windows()

        # 1. Exact match
        for hwnd, title in visible:
            if title.lower() == query_lower:
                return hwnd, title

        # 2. Substring match
        for hwnd, title in visible:
            if query_lower in title.lower():
                return hwnd, title

        return None

    def execute(
        self,
        action: str,
        window_title: Optional[str] = None,
    ) -> ToolResult:
        act = action.lower().strip()

        # 1. List open windows
        if act in ("list", "list_open", "list_windows"):
            windows = self._get_visible_windows()
            if not windows:
                return ToolResult(
                    success=True,
                    output="No visible application windows found.",
                )
            lines = [f"- [{hwnd}] {title}" for hwnd, title in windows[:20]]
            return ToolResult(
                success=True,
                output="Open Windows:\n" + "\n".join(lines),
            )

        # 2. Window-specific actions require window_title
        if not window_title and act not in ("snap_left", "snap_right"):
            return ToolResult(
                success=False,
                output="",
                error=f"Action '{action}' requires 'window_title' to be specified.",
            )

        hwnd_match = self._find_hwnd(window_title) if window_title else None
        hwnd = hwnd_match[0] if hwnd_match else None
        title = hwnd_match[1] if hwnd_match else window_title

        # Focus window
        if act == "focus":
            if not hwnd:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Could not find open window matching '{window_title}'.",
                )
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return ToolResult(
                success=True,
                output=f"Focused window: '{title}'.",
            )

        # Minimize
        if act == "minimize":
            if not hwnd:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Could not find window '{window_title}'.",
                )
            user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            return ToolResult(
                success=True,
                output=f"Minimized window: '{title}'.",
            )

        # Maximize
        if act == "maximize":
            if not hwnd:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Could not find window '{window_title}'.",
                )
            user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
            user32.SetForegroundWindow(hwnd)
            return ToolResult(
                success=True,
                output=f"Maximized window: '{title}'.",
            )

        # Restore
        if act == "restore":
            if not hwnd:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Could not find window '{window_title}'.",
                )
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.SetForegroundWindow(hwnd)
            return ToolResult(
                success=True,
                output=f"Restored window: '{title}'.",
            )

        # Snap left / right (focuses if specified and presses Win+Left / Win+Right)
        if act in ("snap_left", "snap_right"):
            if hwnd:
                user32.ShowWindow(hwnd, 9)
                user32.SetForegroundWindow(hwnd)

            direction = "left" if act == "snap_left" else "right"
            pyautogui.hotkey("win", direction)
            return ToolResult(
                success=True,
                output=f"Snapped active window to the {direction}.",
            )

        return ToolResult(
            success=False,
            output="",
            error=f"Unknown window management action: '{action}'.",
        )
