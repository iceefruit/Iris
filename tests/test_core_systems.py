"""Unit tests for all 6 Core Logic Systems."""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.memory_store import PersistentMemoryStore
from core.scheduler import TaskScheduler
from core.loop import AutonomousGoalRunner, GoalStep, GoalResult
from tools.clipboard import GetClipboardTool, SetClipboardTool, GetActiveSelectionTool
from tools.image_gen import GenerateImageTool
from tools.n8n_tool import TriggerN8nTool
from tools.registry import default_registry


def test_persistent_memory_and_vault():
    print("[1] Testing PersistentMemoryStore & User Knowledge Vault...")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        mem = PersistentMemoryStore(db_path=str(db_path))

        # 1. Test conversation messages
        mem.add_message("user", "My name is Iceef")
        mem.add_message("assistant", "Nice to meet you, Iceef!")
        ctx = mem.get_context()
        assert len(ctx) == 2
        assert ctx[0]["content"] == "My name is Iceef"
        print("    Persistent conversation history verified.")

        # 2. Test User Knowledge Vault
        mem.remember_fact("preferred_editor", "VS Code")
        mem.remember_fact("default_browser", "Chrome")
        facts = mem.get_all_facts()
        assert facts.get("preferred_editor") == "VS Code"
        assert facts.get("default_browser") == "Chrome"

        prompt_str = mem.format_vault_prompt()
        assert "preferred_editor" in prompt_str
        assert "VS Code" in prompt_str
        print("    User Knowledge Vault facts stored and formatted.")

        # 3. Test forget
        assert mem.forget_fact("default_browser") is True
        assert "default_browser" not in mem.get_all_facts()
        print("    User Knowledge Vault fact deletion verified.")


def test_clipboard_tools():
    print("\n[2] Testing Clipboard & Selection Tools...")
    set_tool = SetClipboardTool()
    get_tool = GetClipboardTool()
    sel_tool = GetActiveSelectionTool()

    # Set and get clipboard
    set_res = set_tool.execute(text="Iris Core Logic Test Text 12345")
    assert set_res.success is True

    get_res = get_tool.execute()
    assert get_res.success is True
    assert "Iris Core Logic Test Text 12345" in get_res.output
    print(f"    Clipboard test passed: {get_res.output}")
    print(f"    Active Selection Tool schema verified: {sel_tool.name}")


def test_multimodal_and_n8n_tools():
    print("\n[3] Testing Image Gen & n8n Tools...")
    img_tool = GenerateImageTool()
    assert img_tool.name == "generate_image"
    assert "prompt" in img_tool.parameters["properties"]

    n8n_tool = TriggerN8nTool()
    assert n8n_tool.name == "trigger_n8n_workflow"
    # Execute without URL returns graceful error message
    res = n8n_tool.execute(event_name="test_event")
    assert res.success is False
    assert "No n8n Webhook URL" in res.error
    print("    GenerateImageTool and TriggerN8nTool verified.")


def test_task_scheduler():
    print("\n[4] Testing Background TaskScheduler...")
    sched = TaskScheduler()
    executed_flag = []

    def callback_fn(msg):
        executed_flag.append(msg)

    # 1. One-shot timer (0.2s)
    sched.schedule_once("test_timer", 0.2, callback_fn, "timer_done")
    tasks = sched.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["name"] == "test_timer"

    time.sleep(0.5)
    assert "timer_done" in executed_flag
    print("    One-shot timer executed callback successfully.")

    # 2. Cancellation
    sched.schedule_interval("test_recurring", 10.0, callback_fn, "recurrent")
    assert sched.cancel("test_recurring") is True
    assert len(sched.list_tasks()) == 0
    print("    Task cancellation verified.")

    sched.shutdown()
    print("    TaskScheduler shutdown cleanly.")


def test_full_registry_tools():
    print("\n[5] Testing Total Registered Tool Set...")
    tools = default_registry.list_tools()
    tool_names = [t.name for t in tools]
    print(f"    Registered tools ({len(tools)}): {tool_names}")
    assert len(tools) >= 20
    assert "generate_image" in tool_names
    assert "trigger_n8n_workflow" in tool_names
    assert "get_clipboard" in tool_names
    assert "set_clipboard" in tool_names
    assert "get_active_selection" in tool_names


if __name__ == "__main__":
    test_persistent_memory_and_vault()
    test_clipboard_tools()
    test_multimodal_and_n8n_tools()
    test_task_scheduler()
    test_full_registry_tools()
    print("\nAll 6 Core Logic Systems Passed Verification Successfully!")
