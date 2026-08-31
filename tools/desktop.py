"""Desktop GUI Actuator Tools (Mouse, Keyboard, Hotkeys, Scrolling)."""

import time
from typing import Any, Dict, List, Optional
import pyautogui

from config import config
from tools.base import BaseTool, ToolResult
from vision.capture import ScreenCaptureEngine
from vision.context import SystemContextExtractor

# Enforce fail-safe: slam mouse into screen corner to immediately abort
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def _get_target_pixels(norm_x: int, norm_y: int) -> tuple[int, int]:
    """Converts [0, 1000] normalized coordinates to physical desktop pixels."""
    screen_w, screen_h = SystemContextExtractor.get_screen_resolution()
    return ScreenCaptureEngine.denormalize_coordinates(norm_x, norm_y, screen_w, screen_h)


class ClickTool(BaseTool):
    """Tool for clicking at specific normalized coordinates on the desktop."""

    name = "click"
    description = (
        "Moves mouse cursor and clicks on a target at normalized coordinates (0-1000 scale). "
        "Use [500, 500] for screen center. Supports single, double, right, or middle click."
    )
    parameters = {
        "type": "object",
        "properties": {
            "norm_x": {
                "type": "integer",
                "minimum": 0,
                "maximum": 1000,
                "description": "Normalized X coordinate (0 to 1000)",
            },
            "norm_y": {
                "type": "integer",
                "minimum": 0,
                "maximum": 1000,
                "description": "Normalized Y coordinate (0 to 1000)",
            },
            "button": {
                "type": "string",
                "enum": ["left", "right", "middle"],
                "default": "left",
                "description": "Mouse button to click (default: left)",
            },
            "clicks": {
                "type": "integer",
                "minimum": 1,
                "maximum": 3,
                "default": 1,
                "description": "Number of clicks (1 for single click, 2 for double click)",
            },
        },
        "required": ["norm_x", "norm_y"],
    }

    def execute(
        self,
        norm_x: int,
        norm_y: int,
        button: str = "left",
        clicks: int = 1,
        **kwargs,
    ) -> ToolResult:
        if not config.actuator_enabled:
            return ToolResult(success=False, output="", error="Desktop actuator is disabled in config.")

        px_x, px_y = _get_target_pixels(norm_x, norm_y)
        try:
            duration = config.actuator_mouse_duration
            pyautogui.moveTo(px_x, px_y, duration=duration)
            pyautogui.click(px_x, px_y, clicks=clicks, button=button)
            action_name = "Double-clicked" if clicks == 2 else f"Clicked ({button})"
            return ToolResult(
                success=True,
                output=f"{action_name} at normalized [{norm_x}, {norm_y}] (pixel {px_x}, {px_y}).",
            )
        except pyautogui.FailSafeException:
            return ToolResult(
                success=False,
                output="",
                error="Action aborted: PyAutoGUI FailSafe triggered by user cursor movement.",
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Click failed: {str(e)}")


class MoveCursorTool(BaseTool):
    """Tool for moving the cursor without clicking."""

    name = "move_cursor"
    description = "Moves mouse cursor smoothly to normalized coordinates (0-1000 scale)."
    parameters = {
        "type": "object",
        "properties": {
            "norm_x": {"type": "integer", "minimum": 0, "maximum": 1000},
            "norm_y": {"type": "integer", "minimum": 0, "maximum": 1000},
        },
        "required": ["norm_x", "norm_y"],
    }

    def execute(self, norm_x: int, norm_y: int, **kwargs) -> ToolResult:
        if not config.actuator_enabled:
            return ToolResult(success=False, output="", error="Desktop actuator is disabled.")

        px_x, px_y = _get_target_pixels(norm_x, norm_y)
        try:
            pyautogui.moveTo(px_x, px_y, duration=config.actuator_mouse_duration)
            return ToolResult(
                success=True,
                output=f"Cursor moved to normalized [{norm_x}, {norm_y}] (pixel {px_x}, {px_y}).",
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Move failed: {str(e)}")


class TypeTextTool(BaseTool):
    """Tool for typing text into the currently focused input element."""

    name = "type_text"
    description = "Types string into the currently focused window or field, with optional Enter key."
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The exact string of text to type.",
            },
            "press_enter": {
                "type": "boolean",
                "default": False,
                "description": "Whether to press Enter after typing.",
            },
        },
        "required": ["text"],
    }

    def execute(self, text: str, press_enter: bool = False, **kwargs) -> ToolResult:
        if not config.actuator_enabled:
            return ToolResult(success=False, output="", error="Desktop actuator is disabled.")

        try:
            interval = config.actuator_typing_delay
            pyautogui.write(text, interval=interval)
            if press_enter:
                pyautogui.press("enter")
            return ToolResult(
                success=True,
                output=f"Typed text: {repr(text)}" + (" with Enter" if press_enter else ""),
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Type failed: {str(e)}")


class PressHotkeyTool(BaseTool):
    """Tool for pressing key shortcuts (e.g. Ctrl+C, Alt+Tab, Win+R)."""

    name = "press_hotkey"
    description = (
        "Presses a keyboard hotkey or single key combination. "
        "Examples: ['ctrl', 'c'], ['win', 'r'], ['alt', 'tab'], ['enter'], ['escape']."
    )
    parameters = {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of key names to press in combination (e.g. ['ctrl', 'a']).",
            }
        },
        "required": ["keys"],
    }

    def execute(self, keys: List[str], **kwargs) -> ToolResult:
        if not config.actuator_enabled:
            return ToolResult(success=False, output="", error="Desktop actuator is disabled.")

        if not keys:
            return ToolResult(success=False, output="", error="No keys provided.")

        try:
            # Normalize common key aliases
            normalized_keys = []
            for k in keys:
                k_clean = k.strip().lower()
                if k_clean in ("win", "windows", "super", "cmd"):
                    normalized_keys.append("win")
                elif k_clean in ("control", "ctrl"):
                    normalized_keys.append("ctrl")
                elif k_clean in ("alt", "alternate"):
                    normalized_keys.append("alt")
                elif k_clean in ("shift",):
                    normalized_keys.append("shift")
                else:
                    normalized_keys.append(k_clean)

            if len(normalized_keys) == 1:
                pyautogui.press(normalized_keys[0])
            else:
                pyautogui.hotkey(*normalized_keys)

            return ToolResult(
                success=True,
                output=f"Pressed hotkey combo: {' + '.join(normalized_keys)}",
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Hotkey failed: {str(e)}")


class ScrollTool(BaseTool):
    """Tool for scrolling up or down on the page or window."""

    name = "scroll"
    description = "Scrolls active window or control up (positive amount) or down (negative amount)."
    parameters = {
        "type": "object",
        "properties": {
            "clicks": {
                "type": "integer",
                "description": "Number of scroll clicks. Positive for scroll UP, negative for scroll DOWN.",
            }
        },
        "required": ["clicks"],
    }

    def execute(self, clicks: int, **kwargs) -> ToolResult:
        if not config.actuator_enabled:
            return ToolResult(success=False, output="", error="Desktop actuator is disabled.")

        try:
            # PyAutoGUI scroll units: 100-300 per tick is standard
            pyautogui.scroll(clicks * 100)
            direction = "UP" if clicks > 0 else "DOWN"
            return ToolResult(
                success=True,
                output=f"Scrolled {direction} by {abs(clicks)} ticks.",
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Scroll failed: {str(e)}")


class DragTool(BaseTool):
    """Tool for dragging the mouse from one point to another."""

    name = "drag"
    description = "Drags from normalized [start_x, start_y] to [end_x, end_y]."
    parameters = {
        "type": "object",
        "properties": {
            "start_norm_x": {"type": "integer", "minimum": 0, "maximum": 1000},
            "start_norm_y": {"type": "integer", "minimum": 0, "maximum": 1000},
            "end_norm_x": {"type": "integer", "minimum": 0, "maximum": 1000},
            "end_norm_y": {"type": "integer", "minimum": 0, "maximum": 1000},
            "button": {"type": "string", "enum": ["left", "right"], "default": "left"},
        },
        "required": ["start_norm_x", "start_norm_y", "end_norm_x", "end_norm_y"],
    }

    def execute(
        self,
        start_norm_x: int,
        start_norm_y: int,
        end_norm_x: int,
        end_norm_y: int,
        button: str = "left",
        **kwargs,
    ) -> ToolResult:
        if not config.actuator_enabled:
            return ToolResult(success=False, output="", error="Desktop actuator is disabled.")

        s_px_x, s_px_y = _get_target_pixels(start_norm_x, start_norm_y)
        e_px_x, e_px_y = _get_target_pixels(end_norm_x, end_norm_y)

        try:
            pyautogui.moveTo(s_px_x, s_px_y, duration=config.actuator_mouse_duration)
            pyautogui.dragTo(e_px_x, e_px_y, duration=0.4, button=button)
            return ToolResult(
                success=True,
                output=f"Dragged from [{start_norm_x},{start_norm_y}] to [{end_norm_x},{end_norm_y}].",
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Drag failed: {str(e)}")
