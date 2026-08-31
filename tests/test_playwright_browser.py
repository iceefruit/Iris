"""Unit tests for Playwright Web Automation & Browser Agent Tool."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.playwright_browser import PlaywrightBrowserTool


def test_playwright_tool_schema():
    tool = PlaywrightBrowserTool()
    assert tool.name == "browser_interact"
    assert "action" in tool.parameters["properties"]
    assert "url" in tool.parameters["properties"]
    assert "selector" in tool.parameters["properties"]


def test_playwright_tool_mock_navigate():
    tool = PlaywrightBrowserTool()

    mock_page = MagicMock()
    mock_page.title.return_value = "Example Domain"
    mock_page.url = "https://example.com"
    mock_page.inner_text.return_value = "Example Domain Text Content"

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_p = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser

    with patch("tools.playwright_browser.PLAYWRIGHT_AVAILABLE", True), patch(
        "tools.playwright_browser.sync_playwright"
    ) as mock_sync:
        mock_sync.return_value.__enter__.return_value = mock_p

        res = tool.execute(action="navigate", url="https://example.com")
        assert res.success is True
        assert "Example Domain" in res.output
        assert "https://example.com" in res.output


def test_playwright_tool_mock_screenshot():
    tool = PlaywrightBrowserTool()

    mock_page = MagicMock()
    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_p = MagicMock()
    mock_p.chromium.launch.return_value = mock_browser

    with patch("tools.playwright_browser.PLAYWRIGHT_AVAILABLE", True), patch(
        "tools.playwright_browser.sync_playwright"
    ) as mock_sync:
        mock_sync.return_value.__enter__.return_value = mock_p

        res = tool.execute(action="screenshot", url="https://example.com")
        assert res.success is True
        assert "Saved screenshot to:" in res.output
