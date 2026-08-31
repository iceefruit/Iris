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


def set_clipboard_image(image_path: str) -> bool:
    """Copies an image file to the Windows system clipboard for Ctrl+V pasting."""
    import io
    import os
    import subprocess
    from pathlib import Path

    if not os.path.exists(image_path):
        return False

    # Try PIL BMP/DIB win32clipboard method
    try:
        from PIL import Image
        image = Image.open(image_path)
        output = io.BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]  # Strip 14-byte BMP file header for CF_DIB
        output.close()

        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception:
        pass

    # Fallback to PowerShell System.Windows.Forms.Clipboard
    try:
        norm_path = Path(image_path).resolve()
        ps_cmd = (
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile('{norm_path}'))"
        )
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, timeout=5)
        return res.returncode == 0
    except Exception:
        return False


class SetClipboardImageTool(BaseTool):
    """Tool to copy an image file into system clipboard for direct pasting."""

    name = "set_clipboard_image"
    description = (
        "Copies a local image or screenshot file into the system clipboard. "
        "Allows pasting the image with Ctrl+V into Discord, Slack, browsers, or image editors."
    )
    parameters = {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Absolute or relative path to the image file to copy into clipboard.",
            },
        },
        "required": ["image_path"],
    }

    def execute(self, image_path: str, **kwargs) -> ToolResult:
        if not image_path:
            return ToolResult(success=False, output="", error="image_path is required.")
        success = set_clipboard_image(image_path)
        if success:
            return ToolResult(success=True, output=f"Copied image '{image_path}' to system clipboard.")
        return ToolResult(success=False, output="", error=f"Failed to copy image '{image_path}' to clipboard.")

