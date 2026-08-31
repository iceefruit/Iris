"""Browser URL Dispatcher Tool."""

import webbrowser
from tools.base import BaseTool, ToolResult


class OpenUrlTool(BaseTool):
    """Opens web URLs in the user's default browser."""

    name = "open_browser_url"
    description = "Opens a website URL or web page link in the user's default web browser."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to open (e.g. 'https://github.com', 'google.com').",
            },
            "new_tab": {
                "type": "boolean",
                "default": True,
                "description": "Whether to open in a new browser tab.",
            },
        },
        "required": ["url"],
    }

    def execute(self, url: str, new_tab: bool = True, **kwargs) -> ToolResult:
        url_clean = url.strip()
        if not url_clean:
            return ToolResult(success=False, output="", error="URL string is empty.")

        # Prepend https:// if no scheme is provided
        if not (url_clean.startswith("http://") or url_clean.startswith("https://")):
            url_clean = f"https://{url_clean}"

        try:
            webbrowser.open(url_clean, new=2 if new_tab else 0)
            return ToolResult(success=True, output=f"Opened '{url_clean}' in default web browser.")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to open URL in browser: {str(e)}")
