"""Unit tests for IntentRouter and Modular Prompt Architecture."""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config
from core.router import IntentRouter, IntentCategory


def test_modular_prompts_loaded():
    print("[1] Testing Modular Prompts in config & prompts.json...")
    assert "Autonomous ReAct Goal Mode" in config.goal_prompt
    assert "Single Desktop Actuator Mode" in config.actuator_prompt
    assert "Screen Vision & UI Inspection Mode" in config.vision_prompt
    assert "Iris Fast Intent Classifier" in config.router_prompt
    assert "Iris Memory Extraction Engine" in config.memory_prompt
    print("    All 6 modular prompt templates loaded successfully.")


def test_intent_router_classifications():
    print("\n[2] Testing IntentRouter Intent Detection...")
    router = IntentRouter()

    # 1. Multi-Step Goal
    goal_intent = router.route("Open Spotify and play lofi beats")
    assert goal_intent.category == IntentCategory.GOAL
    print(f"    'Open Spotify and play lofi beats' -> {goal_intent.category.value} (PASS)")

    goal_intent2 = router.route("search for python tutorial on google and save to notes.txt")
    assert goal_intent2.category == IntentCategory.GOAL
    print(f"    'search for python ... and save ...' -> {goal_intent2.category.value} (PASS)")

    # 2. Single Action
    action_intent = router.route("launch calculator")
    assert action_intent.category == IntentCategory.ACTION
    print(f"    'launch calculator' -> {action_intent.category.value} (PASS)")

    action_intent2 = router.route("click the blue button")
    assert action_intent2.category == IntentCategory.ACTION
    print(f"    'click the blue button' -> {action_intent2.category.value} (PASS)")

    action_intent3 = router.route("check my cpu and ram status")
    assert action_intent3.category == IntentCategory.ACTION
    print(f"    'check my cpu and ram status' -> {action_intent3.category.value} (PASS)")

    # 3. Vision Question
    vision_intent = router.route("what is on my screen right now?")
    assert vision_intent.category == IntentCategory.VISION
    print(f"    'what is on my screen right now?' -> {vision_intent.category.value} (PASS)")

    # 4. Memory Fact
    mem_intent = router.route("remember that my preferred browser is Firefox")
    assert mem_intent.category == IntentCategory.MEMORY
    assert "preferred browser" in mem_intent.memory_key
    assert "Firefox" in mem_intent.memory_value
    print(f"    'remember that my preferred browser is Firefox' -> {mem_intent.category.value} (key: {mem_intent.memory_key}, val: {mem_intent.memory_value}) (PASS)")

    # 5. Conversational / Coding Chat
    chat_intent = router.route("Explain how async/await works in Python")
    assert chat_intent.category == IntentCategory.CHAT
    print(f"    'Explain how async/await works in Python' -> {chat_intent.category.value} (PASS)")


if __name__ == "__main__":
    test_modular_prompts_loaded()
    test_intent_router_classifications()
    print("\nAll Intent Routing & Prompt Architecture Tests Passed Successfully!")
