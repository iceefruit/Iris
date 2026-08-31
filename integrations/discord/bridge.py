"""Discord-Iris Bridge: Connecting Discord Userbot Gateway to IrisAgent."""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from config import config
from core.agent import IrisAgent
from integrations.discord.client import DiscordRestClient
from integrations.discord.formatter import DiscordMessageFormatter
from integrations.discord.gateway import DiscordGateway

logger = logging.getLogger("Iris_DiscordBridge")


class DiscordIrisBridge:
    """Listens for Discord messages containing 'iris', executes AI actions, and replies."""

    def __init__(
        self,
        agent: IrisAgent,
        token: Optional[str] = None,
        trigger_word: Optional[str] = None,
        allowed_users: Optional[List[str]] = None,
    ):
        self.agent = agent
        self.token = (token or getattr(config, "discord_user_token", "")).strip()
        self.trigger_word = (trigger_word or getattr(config, "discord_trigger_word", "iris")).strip().lower()
        self.allowed_users = allowed_users or [
            u.strip() for u in getattr(config, "discord_allowed_users", "").split(",") if u.strip()
        ]

        self.gateway = DiscordGateway(
            token=self.token,
            on_message_callback=self._handle_discord_message,
        )
        self.rest_client = DiscordRestClient(token=self.token)
        self.formatter = DiscordMessageFormatter()
        self._bg_task: Optional[asyncio.Task] = None

    @property
    def is_running(self) -> bool:
        return self.gateway._is_running

    def extract_trigger_query(self, raw_content: str, is_dm: bool = False) -> Optional[str]:
        """Checks if content triggers Iris and returns the cleaned query."""
        if not raw_content:
            return None

        clean_text = raw_content.strip()

        # Regex for trigger word boundary: \b(iris)\b
        pattern = rf"\b{re.escape(self.trigger_word)}\b"
        match = re.search(pattern, clean_text, re.IGNORECASE)

        if not match and not is_dm:
            return None

        # Clean query by removing trigger word
        query = re.sub(pattern, "", clean_text, flags=re.IGNORECASE).strip()
        # Clean double spaces
        query = re.sub(r"\s+", " ", query).strip()
        # Strip leading punctuation (commas, colons, hyphens)
        query = re.sub(r"^[,:;!\-\s]+", "", query).strip()
        # Fix space before question mark (e.g. "screen ?" -> "screen?")
        query = re.sub(r"\s+\?", "?", query).strip()
        # Strip trailing commas / colons
        query = re.sub(r"[,:;\-\s]+$", "", query).strip()

        return query if query else "Hello Iris"

    async def _handle_discord_message(self, data: Dict[str, Any]):
        """Processes incoming MESSAGE_CREATE event from Discord Gateway."""
        author = data.get("author", {})
        author_id = str(author.get("id", ""))
        self_id = str(data.get("_gateway_user_id", ""))

        # 1. Ignore own messages
        if self_id and author_id == self_id:
            return

        # 2. Ignore bot accounts
        if author.get("bot", False):
            return

        # 3. Whitelist check (if configured)
        if self.allowed_users and author_id not in self.allowed_users:
            return

        channel_id = str(data.get("channel_id", ""))
        guild_id = data.get("guild_id")
        message_id = str(data.get("id", ""))
        raw_content = data.get("content", "")

        is_dm = not bool(guild_id)
        query = self.extract_trigger_query(raw_content, is_dm=is_dm)
        if not query:
            return

        logger.info(f"[DiscordBridge] Triggered by {author.get('username')} in channel {channel_id}: '{query}'")

        # Run Iris execution asynchronously
        asyncio.create_task(
            self._execute_and_reply(
                channel_id=channel_id,
                message_id=message_id,
                user_query=query,
                sender_name=author.get("global_name") or author.get("username", "User"),
            )
        )

    async def _execute_and_reply(
        self,
        channel_id: str,
        message_id: str,
        user_query: str,
        sender_name: str,
    ):
        """Runs Iris process_input and streams results back to Discord."""
        # Trigger typing indicator
        await self.rest_client.trigger_typing(channel_id)

        response_chunks = []
        status_updates = []

        def _run_sync_pipeline():
            events = []
            for event in self.agent.process_input(user_query):
                events.append(event)
            return events

        try:
            # Run blocking Iris pipeline in worker thread
            events = await asyncio.to_thread(_run_sync_pipeline)

            for ev in events:
                ev_type = ev.get("type")

                if ev_type == "intent_detected":
                    cat = ev.get("category", "")
                    if cat in ("GOAL", "ACTION", "VISION"):
                        status_updates.append(self.formatter.format_intent_badge(cat, ev.get("query", "")))

                elif ev_type == "action_executing":
                    status_updates.append(
                        self.formatter.format_action_call(ev.get("tool", ""), ev.get("arguments", {}))
                    )

                elif ev_type == "action_result":
                    status_updates.append(
                        self.formatter.format_action_result(
                            ev.get("tool", ""), ev.get("result", ""), ev.get("success", True)
                        )
                    )

                elif ev_type == "goal_completed":
                    status_updates.append(self.formatter.format_goal_completed(ev.get("summary", "")))

                elif ev_type == "goal_aborted":
                    status_updates.append(self.formatter.format_goal_aborted(ev.get("reason", "")))

                elif ev_type == "chunk":
                    if ev.get("chunk_type") == "content":
                        response_chunks.append(ev.get("text", ""))

                elif ev_type == "content":
                    response_chunks.append(ev.get("text", ""))

            full_reply = "".join(response_chunks).strip()
            final_message_parts = []

            # Add status badges if any action occurred
            if status_updates:
                final_message_parts.append("\n".join(status_updates))

            if full_reply:
                # Apply custom aesthetic emoji replacements to the text
                styled_reply = self.formatter.format_ai_content(full_reply)
                final_message_parts.append(styled_reply)

            final_text = "\n\n".join(final_message_parts).strip()
            if not final_text:
                bow = self.formatter.emojis.get("white_bow", "<:white_bow:1527313288235581470>")
                sparkle = self.formatter.emojis.get("emoji_024", "<:emoji_024:1541018951926947850>")
                final_text = f"{bow} {sparkle} *Task processed successfully.*"

            # Split into chunks if exceeds Discord length
            chunks = self.formatter.chunk_message(final_text)
            for idx, ch in enumerate(chunks):
                reply_ref = message_id if idx == 0 else None
                await self.rest_client.send_message(channel_id, ch, reply_to_id=reply_ref)
                if len(chunks) > 1:
                    await asyncio.sleep(1.0)

        except Exception as e:
            logger.error(f"[DiscordBridge] Execution error: {e}", exc_info=True)
            sad = self.formatter.emojis.get("kittysad", "<:KittySad:1268275441580376074>")
            await self.rest_client.send_message(
                channel_id,
                f"{sad} **Iris Error:** Failed to execute command: `{str(e)}`",
                reply_to_id=message_id,
            )

    async def start(self):
        """Starts Discord Userbot Gateway and fetches server emojis in background."""
        if not self.token:
            logger.warning("[DiscordBridge] No DISCORD_USER_TOKEN provided in config or .env.")
            return False

        # Dynamically discover and register accessible server emojis
        from integrations.discord.emojis import emoji_registry
        self._emoji_task = asyncio.create_task(emoji_registry.fetch_user_guild_emojis(self.token))

        # Run gateway loop until stopped
        try:
            await self.gateway.run()
        finally:
            if hasattr(self, "_emoji_task") and self._emoji_task and not self._emoji_task.done():
                self._emoji_task.cancel()
        return True

    def start_background(self) -> bool:
        """Starts the Discord bridge in a dedicated background thread."""
        if not self.token:
            logger.warning("[DiscordBridge] No DISCORD_USER_TOKEN provided in config or .env.")
            return False
        if self.is_running:
            return True

        import threading

        def _runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            try:
                loop.run_until_complete(self.start())
            except Exception as e:
                logger.error(f"[DiscordBridge] Background worker error: {e}")
            finally:
                loop.close()

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        """Stops the bridge and cleans up resources."""
        self.gateway.stop()
        if hasattr(self, "_loop") and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.rest_client.close(), self._loop)
