"""Smart Clipboard and Active Screen Selection Tools."""

import time
from typing import Dict, Any, Optional
import pyautogui
import pyperclip

from tools.base import BaseTool, ToolResult


class GetClipboardTool(BaseTool):
    """Tool to read the current system clipboard content."""

    name = "get_clipboard"
    description = "Retrieves the current text content stored in the system clipboard."
    parameters = {
        "type": "object",
        "properties": {},
    }

    def execute(self, **kwargs) -> ToolResult:
        try:
            text = pyperclip.paste()
            if not text:
                return ToolResult(success=True, output="(Clipboard is empty)")
            return ToolResult(success=True, output=text)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to read clipboard: {str(e)}")


class SetClipboardTool(BaseTool):
    """Tool to copy text into the system clipboard."""

    name = "set_clipboard"
    description = "Copies a given string of text into the system clipboard."
    parameters = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to copy to clipboard.",
            },
        },
        "required": ["text"],
    }

    def execute(self, text: str, **kwargs) -> ToolResult:
        try:
            pyperclip.copy(text)
            return ToolResult(success=True, output=f"Copied {len(text)} characters to clipboard.")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to set clipboard: {str(e)}")


class GetActiveSelectionTool(BaseTool):
    """Tool to capture currently selected / highlighted text across any application."""

    name = "get_active_selection"
    description = (
        "Non-destructively captures text currently highlighted by the user in any active window, "
        "restoring the previous clipboard contents after reading."
    )
    parameters = {
        "type": "object",
        "properties": {},
    }

    def execute(self, **kwargs) -> ToolResult:
        original_clip = ""
        try:
            original_clip = pyperclip.paste()
        except Exception:
            pass

        try:
            # Clear clipboard temporarily to detect fresh copy
            pyperclip.copy("")
            time.sleep(0.05)

            # Trigger copy shortcut
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.1)

            selected_text = pyperclip.paste()

            # Restore original clipboard
            if original_clip:
                pyperclip.copy(original_clip)

            if not selected_text:
                return ToolResult(
                    success=False,
                    output="",
                    error="No text was highlighted or selection could not be copied.",
                )

            return ToolResult(success=True, output=selected_text)

        except Exception as e:
            if original_clip:
                try:
                    pyperclip.copy(original_clip)
                except Exception:
                    pass
            return ToolResult(success=False, output="", error=f"Failed to capture selection: {str(e)}")
