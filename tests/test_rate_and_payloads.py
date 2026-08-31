"""Unit tests for Client Rate Limiter, Stacked JSON Actions, and 32k+ Large Payload Uploads."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config
from core.client import MikoClient
from tools.registry import ToolRegistry, default_registry


def test_client_rate_limiter():
    print("[1] Testing Client Rate Limiter (Throttling)...")
    # Set to max 4 req/sec (min interval = 0.25s)
    client = MikoClient(
        base_url="https://api-miko.yokoya.space",
        api_key="test_key",
        max_requests_per_second=4.0,
    )

    t0 = time.time()
    client._throttle()
    client._throttle()
    client._throttle()
    t1 = time.time()

    elapsed = t1 - t0
    # 3 calls at 4 req/s requires at least 2 intervals = 0.50s
    assert elapsed >= 0.45
    print(f"    Throttling verified: 3 requests took {round(elapsed, 3)}s (Expected >= 0.45s).")


def test_stacked_json_action_parsing():
    print("\n[2] Testing Stacked JSON Actions and Arrays...")

    # Case A: JSON Array of multiple actions
    text_array = """
Here are the actions to perform:
```action
[
  { "tool": "move_cursor", "arguments": { "norm_x": 450, "norm_y": 520 } },
  { "tool": "click", "arguments": { "button": "left" } },
  { "tool": "type_text", "arguments": { "text": "search query\\n" } }
]
```
"""
    actions_a = default_registry.extract_action_blocks(text_array)
    assert len(actions_a) == 3
    assert actions_a[0][0] == "move_cursor"
    assert actions_a[1][0] == "click"
    assert actions_a[2][0] == "type_text"
    print(f"    JSON Array parsing: {len(actions_a)} actions extracted successfully.")

    # Case B: Stacked consecutive JSON objects
    text_stacked = """
```action
{
  "tool": "launch_application",
  "arguments": { "app_name": "notepad" }
}
{
  "tool": "type_text",
  "arguments": { "text": "Hello Iris!" }
}
```
"""
    actions_b = default_registry.extract_action_blocks(text_stacked)
    assert len(actions_b) == 2
    assert actions_b[0][0] == "launch_application"
    assert actions_b[1][0] == "type_text"
    print(f"    Stacked JSON objects parsing: {len(actions_b)} actions extracted successfully.")


def test_large_system_prompt_and_user_input_thresholds():
    print("\n[3] Testing 32k+ System Prompt and Large Input Upload Thresholds...")
    assert config.max_inline_system_prompt_chars == 32000
    assert config.max_inline_user_chars == 16000
    print(f"    Max inline system prompt chars: {config.max_inline_system_prompt_chars}")
    print(f"    Max inline user input chars: {config.max_inline_user_chars}")


if __name__ == "__main__":
    test_client_rate_limiter()
    test_stacked_json_action_parsing()
    test_large_system_prompt_and_user_input_thresholds()
    print("\nAll Rate Limiter, Stacked JSONs, and Large Payload Tests Passed Successfully!")
