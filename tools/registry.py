"""Tool Registry for managing and dispatching tool calls in Iris."""

import json
import re
from typing import Any, Dict, List, Optional, Tuple
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


class ToolRegistry:
    """Central registry storing tools and executing dispatched function calls."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registers a new tool in the registry."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Retrieves a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Returns list of all active registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns standard OpenAI / Miko function calling schema list."""
        return [tool.to_schema() for tool in self._tools.values()]

    def format_system_prompt_tools(self) -> str:
        """Generates instructions and tool schemas for inclusion in prompt templates."""
        tool_descs = []
        for t in self._tools.values():
            params_str = json.dumps(t.parameters.get("properties", {}), indent=2)
            tool_descs.append(
                f"### `{t.name}`\n{t.description}\n**Parameters:**\n```json\n{params_str}\n```"
            )
        tools_block = "\n\n".join(tool_descs)

        return (
            "## Available Actuator Tools\n"
            "You have access to the following desktop automation tools to interact with the OS:\n\n"
            f"{tools_block}\n\n"
            "To execute actions, output a JSON action block. You can STACK multiple actions in a JSON array or stack consecutive JSON objects when executing sequential actions in one turn:\n\n"
            "### Stacked Actions Example (JSON Array):\n"
            "```action\n"
            "[\n"
            '  { "tool": "move_cursor", "arguments": { "norm_x": 450, "norm_y": 520 } },\n'
            '  { "tool": "click", "arguments": { "button": "left" } },\n'
            '  { "tool": "type_text", "arguments": { "text": "search query\\n" } }\n'
            "]\n"
            "```\n\n"
            "### Stacked Objects Example:\n"
            "```action\n"
            '{\n  "tool": "click",\n  "arguments": { "norm_x": 500, "norm_y": 500 }\n}\n'
            '{\n  "tool": "type_text",\n  "arguments": { "text": "lofi music" }\n}\n'
            "```\n"
        )

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Executes a tool by name with arguments and captures any exceptions."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool '{tool_name}'. Available: {list(self._tools.keys())}",
            )
        try:
            return tool.execute(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Execution error in tool '{tool_name}': {str(e)}",
            )

    @staticmethod
    def extract_action_blocks(text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Parses single, stacked, or array JSON action blocks from model response text."""
        actions: List[Tuple[str, Dict[str, Any]]] = []

        def _process_item(item: Any):
            if isinstance(item, dict):
                t_name = item.get("tool") or item.get("action") or item.get("name")
                t_args = item.get("arguments") or item.get("params") or item.get("args") or {}
                if not t_args:
                    t_args = {k: v for k, v in item.items() if k not in ("tool", "action", "name")}
                if t_name:
                    actions.append((str(t_name), t_args))

        # Extract content inside code blocks (```action ... ``` or ```json ... ``` or ``` ...)
        code_blocks = re.findall(r"```(?:action|json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
        candidate_texts = list(code_blocks) if code_blocks else [text]

        for candidate in candidate_texts:
            clean = candidate.strip()
            if not clean:
                continue

            # Try parsing complete JSON structure (Object or Array)
            try:
                parsed = json.loads(clean)
                if isinstance(parsed, list):
                    for elem in parsed:
                        _process_item(elem)
                    continue
                elif isinstance(parsed, dict):
                    _process_item(parsed)
                    continue
            except json.JSONDecodeError:
                pass

            # Try incremental multi-JSON decoding for stacked JSON objects
            decoder = json.JSONDecoder()
            idx = 0
            while idx < len(clean):
                while idx < len(clean) and clean[idx] not in ("{", "["):
                    idx += 1
                if idx >= len(clean):
                    break
                try:
                    obj, end_idx = decoder.raw_decode(clean, idx)
                    idx = end_idx
                    if isinstance(obj, list):
                        for elem in obj:
                            _process_item(elem)
                    elif isinstance(obj, dict):
                        _process_item(obj)
                except json.JSONDecodeError:
                    idx += 1

        return actions


def create_default_registry() -> ToolRegistry:
    """Builds and returns a registry populated with default Iris tools."""
    registry = ToolRegistry()
    # GUI Actuator Tools
    registry.register(ClickTool())
    registry.register(MoveCursorTool())
    registry.register(TypeTextTool())
    registry.register(PressHotkeyTool())
    registry.register(ScrollTool())
    registry.register(DragTool())
    # Shell & OS Automation Tools
    registry.register(PowerShellTool())
    registry.register(LaunchAppTool())
    registry.register(OpenUrlTool())
    registry.register(SystemStatusTool())
    registry.register(FileOperationTool())
    # Clipboard & Selection Tools
    registry.register(GetClipboardTool())
    registry.register(SetClipboardTool())
    registry.register(GetActiveSelectionTool())
    # Multimodal & Integrations Tools
    registry.register(GenerateImageTool())
    registry.register(TriggerN8nTool())
    # Research, Codebase RAG & Diagnostic Tools
    registry.register(ReadWebpageTool())
    registry.register(IndexDirectoryTool())
    registry.register(SearchKnowledgeBaseTool())
    registry.register(DiagnoseEnvironmentTool())
    return registry


default_registry = create_default_registry()
