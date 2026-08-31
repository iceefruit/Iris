"""Playwright Interactive Web Automation & Browser Agent Tool for Iris."""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from config import config
from tools.base import BaseTool, ToolResult

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class PlaywrightBrowserTool(BaseTool):
    """Automates web navigation, dynamic SPA element interaction, form filling, and full-page screenshots via Playwright."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or config.vision_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "browser_interact"

    @property
    def description(self) -> str:
        return (
            "Automates interactive web browsing with a real browser engine (Playwright). "
            "Supports navigating to URLs, clicking elements/buttons, typing text into forms, "
            "extracting dynamic JavaScript content, taking web screenshots, and evaluating JavaScript."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "click", "type_text", "get_text", "screenshot", "evaluate_js", "scroll"],
                    "description": "Browser action to execute.",
                },
                "url": {
                    "type": "string",
                    "description": "Target webpage URL (required for 'navigate', optional for subsequent actions).",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector, XPath, or text selector for clicking, typing, or extracting (e.g. 'button#submit', 'input[name=\"q\"]', 'text=Sign In').",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type into input field, or JavaScript code to evaluate.",
                },
                "headless": {
                    "type": "boolean",
                    "description": "Whether to run browser in headless mode (default: true).",
                },
            },
            "required": ["action"],
        }

    def execute(
        self,
        action: str,
        url: Optional[str] = None,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        headless: bool = True,
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                success=False,
                output="",
                error="Playwright is not installed. Please run 'pip install playwright && playwright install chromium'.",
            )

        act = action.lower().strip()

        try:
            with sync_playwright() as p:
                # Launch browser with standard viewport
                browser = p.chromium.launch(
                    headless=headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                page = browser.new_page(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )

                if url:
                    target_url = url if url.startswith(("http://", "https://")) else f"https://{url}"
                    page.goto(target_url, wait_until="domcontentloaded", timeout=20000)

                # 1. Navigate
                if act == "navigate":
                    title = page.title()
                    final_url = page.url
                    # Extract page summary
                    body_text = page.inner_text("body")[:1000]
                    browser.close()
                    return ToolResult(
                        success=True,
                        output=f"Successfully navigated to: {final_url}\nTitle: '{title}'\nPreview:\n{body_text}",
                    )

                # 2. Screenshot
                elif act == "screenshot":
                    img_filename = f"browser_{uuid.uuid4().hex[:8]}.png"
                    img_path = str(self.cache_dir / img_filename)
                    if selector:
                        element = page.locator(selector).first
                        element.screenshot(path=img_path)
                    else:
                        page.screenshot(path=img_path, full_page=True)
                    browser.close()
                    return ToolResult(
                        success=True,
                        output=f"Saved screenshot to: {img_path}",
                    )

                # 3. Click
                elif act == "click":
                    if not selector:
                        browser.close()
                        return ToolResult(success=False, output="", error="Action 'click' requires a 'selector'.")
                    page.click(selector, timeout=10000)
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                    browser.close()
                    return ToolResult(
                        success=True,
                        output=f"Clicked element matching '{selector}'.",
                    )

                # 4. Type Text
                elif act == "type_text":
                    if not selector or text is None:
                        browser.close()
                        return ToolResult(
                            success=False,
                            output="",
                            error="Action 'type_text' requires 'selector' and 'text'.",
                        )
                    page.fill(selector, text, timeout=10000)
                    page.press(selector, "Enter")
                    page.wait_for_load_state("domcontentloaded", timeout=5000)
                    browser.close()
                    return ToolResult(
                        success=True,
                        output=f"Typed '{text}' into '{selector}' and pressed Enter.",
                    )

                # 5. Extract Text
                elif act == "get_text":
                    target_sel = selector or "body"
                    content = page.locator(target_sel).all_inner_texts()
                    full_txt = "\n".join(content)[:3000]
                    browser.close()
                    return ToolResult(
                        success=True,
                        output=f"Extracted Text from '{target_sel}':\n{full_txt}",
                    )

                # 6. Evaluate JS
                elif act == "evaluate_js":
                    if not text:
                        browser.close()
                        return ToolResult(success=False, output="", error="Action 'evaluate_js' requires JS code in 'text'.")
                    res = page.evaluate(text)
                    browser.close()
                    return ToolResult(
                        success=True,
                        output=f"JavaScript Result: {str(res)}",
                    )

                # 7. Scroll
                elif act == "scroll":
                    page.mouse.wheel(0, 500)
                    browser.close()
                    return ToolResult(
                        success=True,
                        output="Scrolled webpage down by 500px.",
                    )

                browser.close()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown browser action: '{action}'.",
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Playwright execution error: {str(e)}",
            )
