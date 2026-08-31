"""Iris desktop and system actuator tools package."""

from tools.base import BaseTool, ToolResult
from tools.desktop import (
    ClickTool,
    MoveCursorTool,
    TypeTextTool,
    PressHotkeyTool,
    ScrollTool,
    DragTool,
)
from tools.shell import PowerShellTool
from tools.app_launcher import LaunchAppTool
from tools.browser import OpenUrlTool
from tools.system import SystemStatusTool
from tools.file_ops import FileOperationTool
from tools.clipboard import GetClipboardTool, SetClipboardTool, GetActiveSelectionTool
from tools.image_gen import GenerateImageTool
from tools.n8n_tool import TriggerN8nTool
from tools.web_scraper import ReadWebpageTool
from tools.rag_tool import IndexDirectoryTool, SearchKnowledgeBaseTool
from tools.diagnostics_tool import DiagnoseEnvironmentTool
from tools.registry import ToolRegistry, default_registry, create_default_registry

__all__ = [
    "BaseTool",
    "ToolResult",
    "ClickTool",
    "MoveCursorTool",
    "TypeTextTool",
    "PressHotkeyTool",
    "ScrollTool",
    "DragTool",
    "PowerShellTool",
    "LaunchAppTool",
    "OpenUrlTool",
    "SystemStatusTool",
    "FileOperationTool",
    "GetClipboardTool",
    "SetClipboardTool",
    "GetActiveSelectionTool",
    "GenerateImageTool",
    "TriggerN8nTool",
    "ReadWebpageTool",
    "IndexDirectoryTool",
    "SearchKnowledgeBaseTool",
    "DiagnoseEnvironmentTool",
    "ToolRegistry",
    "default_registry",
    "create_default_registry",
]
