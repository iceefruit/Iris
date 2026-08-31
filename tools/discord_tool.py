"""Comprehensive Discord Actuator and Dispatch Suite for Iris."""

import asyncio
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import config
from tools.base import BaseTool, ToolResult


def _run_sync(coro):
    """Executes a coroutine synchronously, safely handling active running event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result()
    else:
        return asyncio.run(coro)


class SendDiscordMessageTool(BaseTool):
    """Sends a text message or user mention to Discord via REST API or Desktop GUI fallback."""

    name = "send_discord_message"
    description = (
        "Delivers a message or user mention to a Discord channel or DM. "
        "Supports channel IDs (REST API) and channel/user names like '#general' or '@user' (Desktop GUI)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "channel_id": {
                "type": "string",
                "description": "Discord channel ID, channel name (e.g. '#general', 'general'), or user mention (e.g. '@cat', 'cat').",
            },
            "content": {
                "type": "string",
                "description": "Message text to deliver.",
            },
            "ping_user": {
                "type": "string",
                "description": "Optional username or mention to tag (e.g. 'cat', '@cat').",
            },
        },
        "required": ["channel_id", "content"],
    }

    def __init__(self, rest_client: Optional[Any] = None):
        self.rest_client = rest_client

    def _execute_gui_fallback(self, target: str, content: str, ping_user: Optional[str] = None) -> ToolResult:
        """Automates Discord Desktop application using Quick Switcher (Ctrl+K) and keyboard macros."""
        import pyautogui
        from tools.window_manager import WindowManagerTool
        from tools.app_launcher import LaunchAppTool

        # 1. Ensure Discord is running and focused
        wm = WindowManagerTool()
        focus_res = wm.execute(action="focus", window_title="Discord")
        if not focus_res.success:
            LaunchAppTool().execute(app_name="discord")
            time.sleep(2.0)
            wm.execute(action="focus", window_title="Discord")

        time.sleep(0.3)

        # 2. Quick Switcher (Ctrl+K) to target channel/server/DM
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.2)
        search_term = target.lstrip("#")
        if target.startswith("@"):
            search_term = f"@{target.lstrip('@')}"
        pyautogui.write(search_term, interval=0.02)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)

        # 3. Handle @user mention if specified
        target_ping = ping_user or (target if target.startswith("@") else None)
        if target_ping:
            clean_ping = target_ping.lstrip("@")
            pyautogui.write(f"@{clean_ping}", interval=0.02)
            time.sleep(0.25)
            pyautogui.press("tab")  # Lock Discord mention pill
            pyautogui.write(" ", interval=0.02)

        # 4. Type and send message
        pyautogui.write(content, interval=0.01)
        pyautogui.press("enter")

        return ToolResult(
            success=True,
            output=f"Delivered message to '{target}' via Discord Desktop GUI automation.",
        )

    def execute(self, channel_id: str = "", target: str = "", content: str = "", ping_user: str = "", **kwargs) -> ToolResult:
        dest = channel_id or target
        if not dest:
            return ToolResult(success=False, output="", error="channel_id is required.")

        token = getattr(config, "discord_user_token", "")
        # If token exists, try resolving channel ID (handles numeric IDs, server names like 'gum', channel names like 'general')
        if token:
            from integrations.discord.client import DiscordRestClient
            client = self.rest_client or DiscordRestClient(token=token)

            async def _send():
                actual_channel_id = dest
                if not dest.isdigit():
                    resolved = await client.resolve_channel(dest)
                    if resolved:
                        actual_channel_id = resolved["channel_id"]
                    else:
                        return None

                # Format user mention if ping_user provided
                body = content
                if ping_user:
                    user_info = await client.resolve_user(ping_user)
                    mention_tag = user_info["mention"] if user_info else f"@{ping_user.lstrip('@')}"
                    body = f"{mention_tag} {content}"

                return await client.send_message(channel_id=actual_channel_id, content=body)

            try:
                res = _run_sync(_send())
                if res and "id" in res:
                    return ToolResult(
                        success=True,
                        output=f"Delivered message to Discord channel {dest} (Message ID: {res['id']})",
                    )
            except Exception:
                pass

        # Fallback to Desktop GUI
        try:
            return self._execute_gui_fallback(target=dest, content=content, ping_user=ping_user or None)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Discord GUI delivery failed: {str(e)}")


class SendDiscordFileTool(BaseTool):
    """Sends a local file, image, or screenshot to Discord via REST API or Desktop GUI."""

    name = "send_discord_file"
    description = (
        "Uploads and sends a local file, image, or screenshot to a Discord channel or DM. "
        "Supports channel IDs (REST API) and channel names like '#general' (Desktop GUI clipboard paste)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "channel_id": {
                "type": "string",
                "description": "Discord channel ID, channel name (e.g. '#general'), or user mention.",
            },
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the local file to upload.",
            },
            "caption": {
                "type": "string",
                "description": "Optional text message or caption to accompany the file.",
            },
        },
        "required": ["channel_id", "file_path"],
    }

    def __init__(self, rest_client: Optional[Any] = None):
        self.rest_client = rest_client

    def _execute_gui_fallback(self, target: str, file_path: str, caption: str = "") -> ToolResult:
        """Copies image to clipboard and pastes into Discord or opens file upload dialog."""
        import pyautogui
        from tools.window_manager import WindowManagerTool
        from tools.app_launcher import LaunchAppTool
        from tools.clipboard import set_clipboard_image

        wm = WindowManagerTool()
        focus_res = wm.execute(action="focus", window_title="Discord")
        if not focus_res.success:
            LaunchAppTool().execute(app_name="discord")
            time.sleep(2.0)
            wm.execute(action="focus", window_title="Discord")

        time.sleep(0.3)

        # Quick Switcher to channel
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.2)
        pyautogui.write(target.lstrip("#"), interval=0.02)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)

        # If image, copy to clipboard and paste
        if file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")):
            if set_clipboard_image(file_path):
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.4)
                if caption:
                    pyautogui.write(caption, interval=0.01)
                    time.sleep(0.1)
                pyautogui.press("enter")
                return ToolResult(
                    success=True,
                    output=f"Uploaded image '{os.path.basename(file_path)}' to '{target}' via Discord clipboard paste.",
                )

        # For general files, use Ctrl+Shift+U
        pyautogui.hotkey("ctrl", "shift", "u")
        time.sleep(0.5)
        pyautogui.write(str(Path(file_path).resolve()), interval=0.01)
        pyautogui.press("enter")
        time.sleep(0.5)
        if caption:
            pyautogui.write(caption, interval=0.01)
        pyautogui.press("enter")

        return ToolResult(
            success=True,
            output=f"Uploaded file '{os.path.basename(file_path)}' to '{target}' via Discord GUI.",
        )

    def execute(self, channel_id: str = "", target: str = "", file_path: str = "", caption: str = "", **kwargs) -> ToolResult:
        dest = channel_id or target
        if not dest:
            return ToolResult(success=False, output="", error="channel_id is required.")

        if not file_path or not Path(file_path).exists():
            return ToolResult(success=False, output="", error=f"File not found: '{file_path}'")

        token = getattr(config, "discord_user_token", "")
        # If dest is numerical channel ID and token exists, use REST API
        if token and dest.isdigit():
            from integrations.discord.client import DiscordRestClient
            client = self.rest_client or DiscordRestClient(token=token)

            async def _upload():
                return await client.send_message(channel_id=dest, content=caption, file_path=file_path)

            try:
                res = _run_sync(_upload())
                if res and "id" in res:
                    return ToolResult(
                        success=True,
                        output=f"Sent file '{os.path.basename(file_path)}' to Discord channel {dest} (Message ID: {res['id']})",
                    )
            except Exception:
                pass

        # Fallback to Desktop GUI
        try:
            return self._execute_gui_fallback(target=dest, file_path=file_path, caption=caption)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Discord GUI upload failed: {str(e)}")


class ReadDiscordMessagesTool(BaseTool):
    """Reads recent message history from a Discord channel or server (e.g. 'gum', 'general', 'gum general')."""

    name = "read_discord_messages"
    description = (
        "Reads recent messages from a Discord server, channel, or DM. "
        "Accepts server names (e.g. 'gum'), channel names (e.g. 'general', 'gum general'), or channel IDs. "
        "Automatically searches joined servers and finds the server's #general chat if a server name is provided."
    )
    parameters = {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "Discord server name (e.g. 'gum'), channel name (e.g. '#general', 'gum general'), or channel ID.",
            },
            "channel_id": {
                "type": "string",
                "description": "Alias for target.",
            },
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Number of recent messages to fetch (max 50).",
            },
        },
    }

    def __init__(self, rest_client: Optional[Any] = None):
        self.rest_client = rest_client

    def _execute_gui_fallback(self, target: str) -> ToolResult:
        """Navigates to the Discord channel visually using Quick Switcher (Ctrl+K)."""
        import pyautogui
        import time
        from tools.window_manager import WindowManagerTool
        from tools.app_launcher import LaunchAppTool

        wm = WindowManagerTool()
        focus_res = wm.execute(action="focus", window_title="Discord")
        if not focus_res.success:
            LaunchAppTool().execute(app_name="discord")
            time.sleep(2.0)
            wm.execute(action="focus", window_title="Discord")

        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.2)
        pyautogui.write(target.lstrip("#"), interval=0.02)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)

        return ToolResult(
            success=True,
            output=f"Navigated to '{target}' in Discord Desktop. Inspecting chat on screen.",
        )

    def execute(self, target: str = "", channel_id: str = "", limit: int = 10, **kwargs) -> ToolResult:
        dest = target or channel_id
        if not dest:
            return ToolResult(success=False, output="", error="target or channel_id is required.")

        token = getattr(config, "discord_user_token", "")
        if token:
            from integrations.discord.client import DiscordRestClient
            client = self.rest_client or DiscordRestClient(token=token)

            async def _fetch():
                resolved = await client.resolve_channel(dest)
                if not resolved:
                    return None, None
                msgs = await client.get_messages(resolved["channel_id"], limit=limit)
                return resolved, msgs

            try:
                resolved, messages = _run_sync(_fetch())
                if resolved and messages is not None:
                    formatted = [f"=== Messages in {resolved.get('channel_name', 'channel')} ({resolved.get('guild_name', 'Discord')}) ==="]
                    for msg in reversed(messages):
                        author = msg.get("author", {}).get("global_name") or msg.get("author", {}).get("username", "Unknown")
                        content = msg.get("content", "")
                        timestamp = msg.get("timestamp", "")[:19]
                        formatted.append(f"[{timestamp}] {author}: {content}")

                    return ToolResult(
                        success=True,
                        output="\n".join(formatted) if len(formatted) > 1 else "(No recent messages in this channel)",
                    )
            except Exception:
                pass

        # GUI Fallback: Focus Discord, Quick Switch to channel
        try:
            return self._execute_gui_fallback(dest)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Failed to read Discord: {e}")


class SearchDiscordChannelsTool(BaseTool):
    """Searches for channels across Discord servers by name."""

    name = "search_discord_channels"
    description = (
        "Searches for Discord channels by name (e.g. '#general', 'announcements', 'dev-chat') "
        "across all joined servers or filtered by server name. Returns channel IDs and server names."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Channel name or keyword to search for (e.g. 'general', 'bot-commands').",
            },
            "guild_name": {
                "type": "string",
                "description": "Optional server/guild name to narrow search.",
            },
        },
        "required": ["query"],
    }

    def __init__(self, rest_client: Optional[Any] = None):
        self.rest_client = rest_client

    def execute(self, query: str, guild_name: str = "", **kwargs) -> ToolResult:
        token = getattr(config, "discord_user_token", "")
        if not token:
            return ToolResult(success=False, output="", error="No DISCORD_USER_TOKEN configured.")

        from integrations.discord.client import DiscordRestClient
        client = self.rest_client or DiscordRestClient(token=token)

        try:
            results = _run_sync(client.search_channels(query=query, guild_name=guild_name or None))
            if not results:
                return ToolResult(success=True, output=f"No Discord channels found matching '{query}'.")

            lines = [f"Found {len(results)} matching channel(s):"]
            for r in results[:15]:
                lines.append(f"- {r['channel_name']} (ID: `{r['channel_id']}`) in server **{r['guild_name']}**")
            return ToolResult(success=True, output="\n".join(lines))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Channel search error: {e}")


class SendDiscordDmTool(BaseTool):
    """Sends a private Direct Message to a specific Discord user."""

    name = "send_discord_dm"
    description = (
        "Sends a private Direct Message (DM) to a specific Discord user by username or user ID. "
        "Supports REST API and Desktop GUI fallback."
    )
    parameters = {
        "type": "object",
        "properties": {
            "recipient": {
                "type": "string",
                "description": "The recipient's Discord username, display name, or numeric User ID.",
            },
            "content": {
                "type": "string",
                "description": "Message text to deliver privately.",
            },
            "file_path": {
                "type": "string",
                "description": "Optional local file path to attach.",
            },
        },
        "required": ["recipient", "content"],
    }

    def __init__(self, rest_client: Optional[Any] = None):
        self.rest_client = rest_client

    def execute(self, recipient: str, content: str, file_path: str = "", **kwargs) -> ToolResult:
        token = getattr(config, "discord_user_token", "")
        if token:
            from integrations.discord.client import DiscordRestClient
            client = self.rest_client or DiscordRestClient(token=token)

            async def _run():
                target_user_id = recipient.strip().lstrip("<@!").rstrip(">")
                if not target_user_id.isdigit():
                    resolved = await client.resolve_user(recipient)
                    if resolved:
                        target_user_id = resolved["user_id"]

                if target_user_id.isdigit():
                    res = await client.send_dm(
                        recipient_id=target_user_id,
                        content=content,
                        file_path=file_path if file_path and os.path.exists(file_path) else None,
                    )
                    if res and "id" in res:
                        return True, f"Delivered DM to user {recipient} (Message ID: {res['id']})"
                return False, "REST DM failed"

            try:
                success, msg = _run_sync(_run())
                if success:
                    return ToolResult(success=True, output=msg)
            except Exception:
                pass

        # GUI Fallback: Quick Switcher -> @recipient -> Type message
        send_tool = SendDiscordMessageTool(rest_client=self.rest_client)
        return send_tool._execute_gui_fallback(target=f"@{recipient.lstrip('@')}", content=content)
