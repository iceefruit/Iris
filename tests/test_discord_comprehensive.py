"""Comprehensive Discord Integration and Actuator Test Suite for Iris."""

import asyncio
import json
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.router import IntentCategory, IntentRouter
from integrations.discord.client import DiscordRestClient
from integrations.discord.formatter import DiscordMessageFormatter
from tools.clipboard import SetClipboardImageTool, set_clipboard_image
from tools.desktop import PressHotkeyTool, TypeTextTool
from tools.discord_tool import (
    ReadDiscordMessagesTool,
    SearchDiscordChannelsTool,
    SendDiscordDmTool,
    SendDiscordFileTool,
    SendDiscordMessageTool,
)
from tools.registry import default_registry


# =====================================================================
# 1. Discord REST Client Suite
# =====================================================================

def test_rest_client_init_and_sanitization():
    client = DiscordRestClient(token="  \"test_token_123\"  ")
    assert client.token == "test_token_123"
    assert "Authorization" in client._headers
    assert client._headers["Authorization"] == "test_token_123"


@pytest.mark.anyio
async def test_trigger_typing():
    client = DiscordRestClient(token="valid_token")

    mock_resp = AsyncMock()
    mock_resp.status = 204

    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__.return_value = mock_resp
    client._get_session = AsyncMock(return_value=mock_session)

    res = await client.trigger_typing("123456789")
    assert res is True
    await client.close()


@pytest.mark.anyio
async def test_send_message_plain_text():
    client = DiscordRestClient(token="valid_token")

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value={"id": "msg_001", "content": "Hello World"})

    mock_session = MagicMock()
    mock_session.post.return_value.__aenter__.return_value = mock_resp
    client._get_session = AsyncMock(return_value=mock_session)

    res = await client.send_message(channel_id="12345", content="Hello World")
    assert res is not None
    assert res["id"] == "msg_001"
    await client.close()


@pytest.mark.anyio
async def test_get_messages():
    client = DiscordRestClient(token="valid_token")

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(
        return_value=[
            {"id": "1", "author": {"username": "alice"}, "content": "hi", "timestamp": "2026-08-31T12:00:00Z"},
            {"id": "2", "author": {"username": "bob"}, "content": "hello", "timestamp": "2026-08-31T12:01:00Z"},
        ]
    )

    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp
    client._get_session = AsyncMock(return_value=mock_session)

    messages = await client.get_messages(channel_id="12345", limit=5)
    assert messages is not None
    assert len(messages) == 2
    assert messages[0]["author"]["username"] == "alice"
    await client.close()


@pytest.mark.anyio
async def test_search_channels_and_resolve_user():
    client = DiscordRestClient(token="valid_token")

    # Mock fetch_user_guilds & fetch_guild_channels
    client.fetch_user_guilds = AsyncMock(return_value=[{"id": "g1", "name": "GUM Server"}])
    client.fetch_guild_channels = AsyncMock(
        return_value=[
            {"id": "c1", "name": "general", "type": 0, "topic": ""},
            {"id": "c2", "name": "dev-chat", "type": 0, "topic": ""},
        ]
    )
    client.fetch_relationships = AsyncMock(
        return_value=[{"user": {"id": "u1", "username": "cat", "global_name": "catftw"}}]
    )

    channels = await client.search_channels(query="general")
    assert len(channels) == 1
    assert channels[0]["channel_name"] == "#general"
    assert channels[0]["channel_id"] == "c1"

    user = await client.resolve_user(query="cat")
    assert user is not None
    assert user["user_id"] == "u1"
    assert user["mention"] == "<@u1>"

    # Test smart channel resolver given server name 'gum'
    resolved = await client.resolve_channel(query="gum")
    assert resolved is not None
    assert resolved["channel_name"] == "#general"
    assert resolved["channel_id"] == "c1"
    assert resolved["guild_name"] == "GUM Server"

    # Test compound query 'gum dev-chat'
    resolved_dev = await client.resolve_channel(query="gum dev-chat")
    assert resolved_dev is not None
    assert resolved_dev["channel_name"] == "#dev-chat"
    assert resolved_dev["channel_id"] == "c2"

    await client.close()


@pytest.mark.anyio
async def test_read_discord_messages_resolves_server():
    client = DiscordRestClient(token="valid_token")
    client.fetch_user_guilds = AsyncMock(return_value=[{"id": "g1", "name": "GUM"}])
    client.fetch_guild_channels = AsyncMock(
        return_value=[{"id": "c1", "name": "general", "type": 0, "topic": ""}]
    )
    client.get_messages = AsyncMock(
        return_value=[{"id": "m1", "author": {"username": "cat"}, "content": "hello", "timestamp": "2026-08-31"}]
    )

    tool = ReadDiscordMessagesTool(rest_client=client)
    with patch("config.config.discord_user_token", "valid_token"):
        res = tool.execute(target="gum")
        assert res.success is True
        assert "Messages in #general (GUM)" in res.output
        assert "cat: hello" in res.output


# =====================================================================
# 2. Discord Actuator Tools Suite
# =====================================================================

def test_discord_tools_registered():
    assert default_registry.get("send_discord_message") is not None
    assert default_registry.get("send_discord_file") is not None
    assert default_registry.get("read_discord_messages") is not None
    assert default_registry.get("search_discord_channels") is not None
    assert default_registry.get("send_discord_dm") is not None
    assert default_registry.get("set_clipboard_image") is not None


def test_send_discord_message_gui_fallback():
    tool = SendDiscordMessageTool()
    with patch("pyautogui.hotkey") as mock_hotkey, \
         patch("pyautogui.write") as mock_write, \
         patch("pyautogui.press") as mock_press, \
         patch("tools.window_manager.WindowManagerTool.execute") as mock_wm:
        mock_wm.return_value = MagicMock(success=True)

        res = tool.execute(target="general", content="Hello team", ping_user="cat")
        assert res.success is True
        assert "Discord Desktop GUI automation" in res.output

        # Verify Quick Switcher & typing
        mock_hotkey.assert_any_call("ctrl", "k")
        mock_write.assert_any_call("general", interval=0.02)
        mock_write.assert_any_call("@cat", interval=0.02)
        mock_press.assert_any_call("tab")
        mock_write.assert_any_call("Hello team", interval=0.01)


def test_send_discord_file_missing_file():
    tool = SendDiscordFileTool()
    res = tool.execute(target="general", file_path="non_existent_file_xyz.png")
    assert res.success is False
    assert "File not found" in res.error


def test_read_discord_messages_no_token():
    with patch("config.config.discord_user_token", ""), \
         patch("pyautogui.hotkey"), \
         patch("pyautogui.write"), \
         patch("pyautogui.press"), \
         patch("tools.window_manager.WindowManagerTool.execute", return_value=MagicMock(success=True)):
        tool = ReadDiscordMessagesTool()
        res = tool.execute(channel_id="12345")
        assert res.success is True
        assert "Navigated to" in res.output


def test_set_clipboard_image_tool():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"dummy image bytes")
        tmp_path = f.name

    try:
        tool = SetClipboardImageTool()
        with patch("tools.clipboard.set_clipboard_image", return_value=True):
            res = tool.execute(image_path=tmp_path)
            assert res.success is True
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# =====================================================================
# 3. Intent Router Discord Formulations Suite
# =====================================================================

@pytest.mark.parametrize(
    "query,expected_category",
    [
        ("go to gum server and tell cat that mgonna be busy today", IntentCategory.GOAL),
        ("switch to discord and send hello to general", IntentCategory.GOAL),
        ("dm alex on discord are you free?", IntentCategory.GOAL),
        ("direct message bob check your email", IntentCategory.GOAL),
        ("ping @cat in general channel saying meeting in 5m", IntentCategory.GOAL),
        ("send this screenshot to general on discord", IntentCategory.GOAL),
        ("check discord messages", IntentCategory.GOAL),
        ("what did alex say on discord", IntentCategory.GOAL),
        ("reply to alex on discord saying looks good", IntentCategory.GOAL),
        ("remember that my discord channel is #dev-chat", IntentCategory.MEMORY),
        ("how do discord webhooks work in python?", IntentCategory.CHAT),
    ],
)
def test_discord_router_classifications(query, expected_category):
    router = IntentRouter()
    parsed = router.route(query)
    assert parsed.category == expected_category


# =====================================================================
# 4. Desktop Quick Switcher & Mention Typing Sequences
# =====================================================================

def test_press_hotkey_tool_normalization():
    tool = PressHotkeyTool()
    with patch("pyautogui.hotkey") as mock_hotkey:
        res = tool.execute(keys=["Ctrl", "K"])
        assert res.success is True
        mock_hotkey.assert_called_once_with("ctrl", "k")


def test_type_text_tool_with_enter():
    tool = TypeTextTool()
    with patch("pyautogui.write") as mock_write, patch("pyautogui.press") as mock_press:
        res = tool.execute(text="#general", press_enter=True)
        assert res.success is True
        mock_write.assert_called_once_with("#general", interval=0.02)
        mock_press.assert_called_once_with("enter")


# =====================================================================
# 5. Discord Formatter & Emojis Suite
# =====================================================================

def test_discord_formatter_codeblock_chunking():
    formatter = DiscordMessageFormatter()
    long_code = "```python\n" + ("x = 1\n" * 400) + "```"
    chunks = formatter.chunk_message(long_code, max_length=500)

    assert len(chunks) > 1
    # Check that each chunk is within safe bounds
    for chunk in chunks:
        assert len(chunk) <= 600
        # Codeblock formatting is preserved
        if "```" in chunk:
            assert chunk.startswith("```") or chunk.endswith("```")


def test_discord_formatter_mention_replacement():
    formatter = DiscordMessageFormatter()
    raw = "Hey @cat and @iceefruit check this out"
    mapping = {"cat": "111222333", "iceefruit": "444555666"}
    res = formatter.format_user_mentions(raw, mapping)
    assert "<@111222333>" in res
    assert "<@444555666>" in res
