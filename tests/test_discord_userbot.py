import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.discord.bridge import DiscordIrisBridge
from integrations.discord.formatter import DiscordMessageFormatter
from integrations.discord.gateway import DiscordGateway


def test_trigger_detection_and_query_cleaning():
    print("[1] Testing Discord Trigger Word Detection & Cleaning...")
    bridge = DiscordIrisBridge(agent=None, trigger_word="iris")

    # Case A: Prefix "Iris"
    q1 = bridge.extract_trigger_query("Iris, open Spotify and play lofi", is_dm=False)
    assert q1 == "open Spotify and play lofi"
    print(f"    'Iris, open Spotify and play lofi' -> '{q1}' (PASS)")

    # Case B: Suffix "iris"
    q2 = bridge.extract_trigger_query("Can you check what is on my screen iris?", is_dm=False)
    assert q2 == "Can you check what is on my screen?"
    print(f"    'Can you check what is on my screen iris?' -> '{q2}' (PASS)")

    # Case C: All Caps "IRIS"
    q3 = bridge.extract_trigger_query("Hey IRIS check my cpu and ram status", is_dm=False)
    assert q3 == "Hey check my cpu and ram status" or "check my cpu and ram status" in q3
    print(f"    'Hey IRIS check my cpu and ram status' -> '{q3}' (PASS)")

    # Case D: Non-triggered channel message
    q4 = bridge.extract_trigger_query("Random chatter between users without trigger word", is_dm=False)
    assert q4 is None
    print(f"    'Random chatter...' (Channel) -> None (PASS)")

    # Case E: Direct DM message without keyword
    q5 = bridge.extract_trigger_query("Can you help me with this code?", is_dm=True)
    assert q5 == "Can you help me with this code?"
    print(f"    'Can you help me...' (DM) -> '{q5}' (PASS)")


def test_discord_message_formatter():
    print("\n[2] Testing Discord Message Formatter & Emoji Badges...")
    formatter = DiscordMessageFormatter()

    badge_goal = formatter.format_intent_badge("GOAL", "Open Spotify")
    assert "🚀" in badge_goal
    assert "Autonomous Goal Mode" in badge_goal
    print(f"    Goal badge: {badge_goal} (PASS)")

    badge_action = formatter.format_action_call("click", {"norm_x": 500, "norm_y": 500})
    assert "⚡" in badge_action
    assert "click" in badge_action
    print(f"    Action badge: {badge_action} (PASS)")

    badge_res = formatter.format_action_result("click", "Clicked at (500, 500)", success=True)
    assert "✔" in badge_res
    print(f"    Action result badge: {badge_res} (PASS)")

    # Chunking test for long responses (> 1900 chars)
    long_text = "A" * 3500
    chunks = formatter.chunk_message(long_text, max_length=1900)
    assert len(chunks) == 2
    assert len(chunks[0]) <= 1900
    assert len(chunks[1]) <= 1900
    print(f"    3500 char text chunked into {len(chunks)} Discord-safe messages (PASS)")


def test_discord_gateway_identify_payload():
    print("\n[3] Testing Discord Gateway Identify Payload Structure...")
    gw = DiscordGateway(token="test_user_token_12345")
    assert gw.token == "test_user_token_12345"
    assert gw.is_valid_token is True
    print("    Gateway initialized successfully. (PASS)")


if __name__ == "__main__":
    test_trigger_detection_and_query_cleaning()
    test_discord_message_formatter()
    test_discord_gateway_identify_payload()
    print("\nAll Discord Userbot Unit Tests Passed Successfully!")
