"""Unit tests for Extended OS Automation Tools and Global Panic Killswitch."""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.killswitch import GlobalPanicKillswitch
from tools.app_launcher import LaunchAppTool
from tools.browser import OpenUrlTool
from tools.system import SystemStatusTool
from tools.file_ops import FileOperationTool
from tools.registry import default_registry


def test_killswitch():
    print("[1] Testing GlobalPanicKillswitch...")
    ks = GlobalPanicKillswitch()
    assert ks.is_aborted is False
    ks.trigger()
    assert ks.is_aborted is True
    print("    Killswitch triggered -> is_aborted is True")
    ks.reset()
    assert ks.is_aborted is False
    print("    Killswitch reset -> is_aborted is False")


def test_system_status():
    print("\n[2] Testing SystemStatusTool...")
    sys_tool = SystemStatusTool()
    res = sys_tool.execute(include_top_processes=True)
    assert res.success is True
    data = json.loads(res.output)
    assert "cpu_utilization" in data
    assert "ram_usage" in data
    assert "disks" in data
    assert "active_window" in data
    print(f"    CPU: {data['cpu_utilization']}, RAM: {data['ram_usage']}")
    print(f"    Active Window: {data['active_window']}")


def test_file_operations():
    print("\n[3] Testing FileOperationTool...")
    file_tool = FileOperationTool()

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test_iris.txt"

        # 1. Write
        w_res = file_tool.execute(operation="write", path=str(test_file), content="Hello Iris!\nLine 2")
        assert w_res.success is True
        print(f"    Write: {w_res.output}")

        # 2. Read
        r_res = file_tool.execute(operation="read", path=str(test_file))
        assert r_res.success is True
        assert "Hello Iris!" in r_res.output
        print(f"    Read content: {r_res.output.strip()}")

        # 3. Append
        a_res = file_tool.execute(operation="append", path=str(test_file), content="\nLine 3 appended")
        assert a_res.success is True

        # 4. List Dir
        l_res = file_tool.execute(operation="list_dir", path=tmpdir)
        assert l_res.success is True
        assert "test_iris.txt" in l_res.output
        print(f"    List Dir: {l_res.output.strip()}")

        # 5. Search
        s_res = file_tool.execute(operation="search", path=tmpdir, pattern="*.txt")
        assert s_res.success is True
        assert "test_iris.txt" in s_res.output
        print(f"    Search: {s_res.output.strip()}")

        # 6. Safe Delete (Recycle Bin)
        d_res = file_tool.execute(operation="delete", path=str(test_file))
        assert d_res.success is True
        assert not test_file.exists()
        print(f"    Recycled: {d_res.output}")


def test_app_launcher_and_browser():
    print("\n[4] Testing AppLauncher and Browser Tools...")
    launcher = LaunchAppTool()
    assert launcher.name == "launch_application"
    assert "app_name" in launcher.parameters["properties"]

    browser_tool = OpenUrlTool()
    assert browser_tool.name == "open_browser_url"
    assert "url" in browser_tool.parameters["properties"]
    print("    LaunchAppTool and OpenUrlTool schemas validated.")


def test_registry_has_all_tools():
    print("\n[5] Testing Full Registry Tool Set...")
    tools = default_registry.list_tools()
    tool_names = [t.name for t in tools]
    print(f"    Total Registered Tools ({len(tools)}): {tool_names}")
    assert len(tools) >= 20
    assert "launch_application" in tool_names
    assert "open_browser_url" in tool_names
    assert "get_system_status" in tool_names
    assert "file_operation" in tool_names


if __name__ == "__main__":
    test_killswitch()
    test_system_status()
    test_file_operations()
    test_app_launcher_and_browser()
    test_registry_has_all_tools()
    print("\nAll Extended Tools & Killswitch Tests Passed Successfully!")
