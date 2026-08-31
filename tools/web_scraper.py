"""Headless Web Scraper and Clean Markdown Article Reader Tool."""

import re
from typing import Dict, Any, Optional
import httpx
from tools.base import BaseTool, ToolResult


class ReadWebpageTool(BaseTool):
    """Tool for fetching and reading web pages directly into clean Markdown text."""

    name = "read_webpage"
    description = (
        "Fetches and extracts clean, readable text/markdown from any website URL or article "
        "without opening a GUI browser window. Strips ads, scripts, and clutter."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the webpage or article to read.",
            },
            "max_chars": {
                "type": "integer",
                "default": 8000,
                "description": "Maximum number of characters to extract (default: 8000).",
            },
        },
        "required": ["url"],
    }

    def _html_to_markdown(self, html: str) -> str:
        """Converts raw HTML into clean structured Markdown text."""
        # 1. Remove script, style, header, footer, nav, svg tags
        text = re.sub(r"<(script|style|nav|header|footer|aside|svg|noscript)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        
        # 2. Extract Title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.DOTALL | re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else "Webpage Content"

        # 3. Convert Headings
        for i in range(6, 0, -1):
            text = re.sub(rf"<h{i}[^>]*>(.*?)</h{i}>", rf"\n\n{'#' * i} \1\n\n", text, flags=re.DOTALL | re.IGNORECASE)

        # 4. Convert Paragraphs and Line Breaks
        text = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\n\1\n\n", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

        # 5. Convert List Items
        text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL | re.IGNORECASE)

        # 6. Convert Code Blocks & Inline Code
        text = re.sub(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", r"\n```\n\1\n```\n", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=re.DOTALL | re.IGNORECASE)

        # 7. Strip all remaining HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # 8. Clean up whitespace
        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n".join([line for line in lines if line])
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        return f"# {title}\n\n{cleaned}"

    def execute(self, url: str, max_chars: int = 8000, **kwargs) -> ToolResult:
        clean_url = url.strip()
        if not clean_url:
            return ToolResult(success=False, output="", error="URL is empty.")

        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = f"https://{clean_url}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                res = client.get(clean_url, headers=headers)
                if res.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to fetch webpage [{res.status_code}]: {res.reason_phrase}",
                    )

                content_type = res.headers.get("content-type", "")
                if "text/html" not in content_type and "application" in content_type:
                    # Direct text / json
                    text = res.text[:max_chars]
                    return ToolResult(success=True, output=f"Direct Content:\n\n{text}")

                markdown_doc = self._html_to_markdown(res.text)
                truncated = markdown_doc[:max_chars]
                if len(markdown_doc) > max_chars:
                    truncated += f"\n\n... [Content truncated at {max_chars} characters]"

                return ToolResult(success=True, output=truncated)

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Web scraping failed: {str(e)}")
