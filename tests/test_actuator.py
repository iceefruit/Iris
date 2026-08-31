"""Unit tests for Visual Grounding Grid & Desktop Actuator Tools."""

import os
import sys
from pathlib import Path
from PIL import Image

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyautogui
from vision.grid import draw_coordinate_grid
from vision.capture import ScreenCaptureEngine
from vision.engine import VisionEngine
from tools.registry import default_registry, ToolRegistry
from tools.desktop import ClickTool, MoveCursorTool, TypeTextTool, PressHotkeyTool
from tools.shell import PowerShellTool


def test_visual_grounding_grid():
    print("[1] Testing Visual Grounding Coordinate Grid...")
    base_img = Image.new("RGB", (1920, 1080), color=(40, 40, 45))
    grid_img = draw_coordinate_grid(base_img, step=100)
    assert grid_img.size == (1920, 1080)
    
    # Verify image was modified
    assert grid_img.tobytes() != base_img.tobytes()
    print("    Coordinate Grid rendered successfully on 1920x1080 canvas.")


def test_tool_registry():
    print("\n[2] Testing ToolRegistry...")
    tools = default_registry.list_tools()
    tool_names = [t.name for t in tools]
    print(f"    Registered tools ({len(tools)}): {tool_names}")

    expected_tools = [
        "click",
        "move_cursor",
        "type_text",
        "press_hotkey",
        "scroll",
        "drag",
        "execute_powershell",
    ]
    for exp in expected_tools:
        assert exp in tool_names, f"Missing tool: {exp}"

    # Test schemas
    schemas = default_registry.get_schemas()
    assert len(schemas) == len(tools)
    assert schemas[0]["type"] == "function"
    print("    OpenAI/Miko Function Schemas verified.")

    # Test prompt formatting
    sys_prompt_tools = default_registry.format_system_prompt_tools()
    assert "## Available Actuator Tools" in sys_prompt_tools
    assert "```action" in sys_prompt_tools
    print("    System Prompt Tool Description block generated.")

    # Test action block extraction
    mock_model_output = """
I will now click on the submit button.
```action
{
  "tool": "click",
  "arguments": {
    "norm_x": 500,
    "norm_y": 500,
    "button": "left"
  }
}
```
Done!
"""
    actions = ToolRegistry.extract_action_blocks(mock_model_output)
    assert len(actions) == 1
    assert actions[0][0] == "click"
    assert actions[0][1]["norm_x"] == 500
    assert actions[0][1]["norm_y"] == 500
    print(f"    Action block extracted: {actions[0]}")


def test_powershell_execution():
    print("\n[3] Testing PowerShell Execution Tool...")
    ps_tool = PowerShellTool()
    res = ps_tool.execute(command='Write-Output "Iris Actuator Test OK"')
    assert res.success is True
    assert "Iris Actuator Test OK" in res.output
    print(f"    PowerShell execution success: {res.output}")


def test_pyautogui_safety():
    print("\n[4] Testing PyAutoGUI & Safety Guarantees...")
    assert pyautogui.FAILSAFE is True, "FAILSAFE must be True for user safety!"
    print("    pyautogui.FAILSAFE is True (Fail-safe corner abort active).")


def test_vision_engine_with_grid():
    print("\n[5] Testing Vision Engine with Grid Overlay...")
    engine = VisionEngine()
    prompt, img_path, context = engine.capture_with_context(
        user_query="Inspect grid coordinates",
        with_grid=True,
    )
    assert Path(img_path).exists()
    assert os.path.getsize(img_path) > 0
    print(f"    Screenshot with Grid saved: {img_path}")


if __name__ == "__main__":
    test_visual_grounding_grid()
    test_tool_registry()
    test_powershell_execution()
    test_pyautogui_safety()
    test_vision_engine_with_grid()
    print("\nAll Actuator & Visual Grounding Tests Passed Successfully!")
