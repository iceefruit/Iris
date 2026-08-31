"""Discord REST API Client for User Account Interaction."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import aiohttp

logger = logging.getLogger("Iris_DiscordClient")


class DiscordRestClient:
    """Sends messages, replies, and simulates typing via Discord HTTP API."""

    def __init__(self, token: str):
        self.token = token.strip().strip('"').strip("'")
        self.base_url = "https://discord.com/api/v9"
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers = {
            "Authorization": self.token,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) discord/1.0.9171 Chrome/128.0.6613.186 Electron/32.2.6 Safari/537.36"
            ),
            "Content-Type": "application/json",
            "Accept": "*/*",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or getattr(self._session, "closed", False) is True:
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session

    async def close(self):
        if self._session and getattr(self._session, "closed", False) is False:
            if asyncio.iscoroutinefunction(getattr(self._session, "close", None)):
                await self._session.close()
            elif callable(getattr(self._session, "close", None)):
                self._session.close()

    async def trigger_typing(self, channel_id: str) -> bool:
        """Triggers the typing indicator in a channel."""
        url = f"{self.base_url}/channels/{channel_id}/typing"
        session = await self._get_session()
        try:
            async with session.post(url) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    async def send_message(
        self,
        channel_id: str,
        content: str,
        reply_to_id: Optional[str] = None,
        file_path: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Sends a text message, reply, or file attachment to a Discord channel."""
        import json
        import os
        from pathlib import Path

        url = f"{self.base_url}/channels/{channel_id}/messages"
        payload: Dict[str, Any] = {"content": content}

        if reply_to_id:
            payload["message_reference"] = {"message_id": str(reply_to_id)}
            payload["allowed_mentions"] = {"replied_user": False}

        session = await self._get_session()

        for attempt in range(3):
            try:
                # Check if we are attaching a file
                if file_path or file_bytes:
                    data = aiohttp.FormData()
                    data.add_field("payload_json", json.dumps(payload))

                    if file_path and Path(file_path).exists():
                        fname = filename or os.path.basename(file_path)
                        with open(file_path, "rb") as f:
                            raw_content = f.read()
                        data.add_field("files[0]", raw_content, filename=fname)
                    elif file_bytes:
                        fname = filename or "attachment.png"
                        data.add_field("files[0]", file_bytes, filename=fname)

                    # Custom headers without Content-Type so aiohttp sets multipart/form-data boundary
                    custom_headers = {k: v for k, v in self._headers.items() if k.lower() != "content-type"}
                    async with session.post(url, data=data, headers=custom_headers) as resp:
                        if resp.status in (200, 201):
                            return await resp.json()
                        elif resp.status == 429:
                            resp_data = await resp.json()
                            retry_after = resp_data.get("retry_after", 2.0)
                            logger.warning(f"[DiscordRestClient] Rate limited. Retrying after {retry_after}s...")
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            err_text = await resp.text()
                            logger.error(f"[DiscordRestClient] Send with attachment failed [{resp.status}]: {err_text}")
                            return None
                else:
                    async with session.post(url, json=payload) as resp:
                        if resp.status in (200, 201):
                            return await resp.json()
                        elif resp.status == 429:
                            data = await resp.json()
                            retry_after = data.get("retry_after", 2.0)
                            logger.warning(f"[DiscordRestClient] Rate limited. Retrying after {retry_after}s...")
                            await asyncio.sleep(retry_after)
                            continue
                        else:
                            err_text = await resp.text()
                            logger.error(f"[DiscordRestClient] Send failed [{resp.status}]: {err_text}")
                            return None
            except Exception as e:
                logger.error(f"[DiscordRestClient] HTTP request error: {e}")
                await asyncio.sleep(1.0)
        return None

    async def get_messages(self, channel_id: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Fetches recent messages from a Discord channel or DM."""
        url = f"{self.base_url}/channels/{channel_id}/messages?limit={min(max(1, limit), 50)}"
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                err = await resp.text()
                logger.error(f"[DiscordRestClient] get_messages failed [{resp.status}]: {err}")
                return None
        except Exception as e:
            logger.error(f"[DiscordRestClient] get_messages error: {e}")
            return None

    async def fetch_user_guilds(self) -> List[Dict[str, Any]]:
        """Fetches all guilds/servers the user account is a member of."""
        url = f"{self.base_url}/users/@me/guilds?limit=100"
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"[DiscordRestClient] fetch_user_guilds error: {e}")
        return []

    async def fetch_guild_channels(self, guild_id: str) -> List[Dict[str, Any]]:
        """Fetches all channels in a guild."""
        url = f"{self.base_url}/guilds/{guild_id}/channels"
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"[DiscordRestClient] fetch_guild_channels error: {e}")
        return []

    async def search_channels(
        self, query: str, guild_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Searches for channels matching query (by name or topic) across joined guilds."""
        clean_query = query.strip().lstrip("#").lower()
        guilds = await self.fetch_user_guilds()
        results = []

        for g in guilds:
            g_name = g.get("name", "")
            if guild_name and guild_name.lower() not in g_name.lower():
                continue
            g_id = g.get("id")
            channels = await self.fetch_guild_channels(g_id)
            for ch in channels:
                if ch.get("type") in (0, 5, 11, 12):  # Text, Announcements, Threads
                    ch_name = ch.get("name", "").lower()
                    topic = (ch.get("topic") or "").lower()
                    if clean_query in ch_name or clean_query in topic:
                        results.append({
                            "channel_id": str(ch["id"]),
                            "channel_name": f"#{ch.get('name')}",
                            "guild_id": str(g_id),
                            "guild_name": g_name,
                            "type": ch.get("type"),
                            "topic": ch.get("topic") or "",
                        })
        return results

    async def resolve_channel(
        self, query: str, guild_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Smart resolver that finds a channel or defaults to #general in a server.
        
        Handles:
        - Numerical ID: '1280406522190495884' -> returns channel ID.
        - Server name: 'gum' -> finds server 'gum', returns its #general or default chat channel.
        - Compound query: 'gum general', 'gum #dev' -> finds server 'gum', returns target channel.
        - Channel name: 'general' -> searches for #general across joined guilds.
        """
        raw = query.strip()
        if raw.isdigit():
            return {"channel_id": raw, "channel_name": f"Channel {raw}", "guild_name": "Discord"}

        clean = raw.lower().replace("server", "").replace("channel", "").strip()
        parts = clean.split()

        guilds = await self.fetch_user_guilds()
        if not guilds:
            return None

        # 1. Check if user passed guild_name explicitly or compound query (e.g. 'gum general')
        target_guild = None
        target_channel_name = None

        if guild_name:
            for g in guilds:
                if guild_name.lower() in g.get("name", "").lower():
                    target_guild = g
                    break
            target_channel_name = clean.lstrip("#")
        elif len(parts) >= 2:
            potential_guild_name = parts[0]
            potential_chan_name = " ".join(parts[1:]).lstrip("#")
            for g in guilds:
                if potential_guild_name in g.get("name", "").lower():
                    target_guild = g
                    target_channel_name = potential_chan_name
                    break

        # 2. Check if the entire query matches a Guild Name (e.g. 'gum')
        if not target_guild:
            for g in guilds:
                if clean in g.get("name", "").lower() or g.get("name", "").lower() in clean:
                    target_guild = g
                    target_channel_name = "general"
                    break

        # 3. If target_guild found, find target_channel_name or default general/chat
        if target_guild:
            g_id = target_guild.get("id")
            g_name = target_guild.get("name", "")
            channels = await self.fetch_guild_channels(g_id)
            text_channels = [ch for ch in channels if ch.get("type") in (0, 5, 11, 12)]

            if target_channel_name:
                for ch in text_channels:
                    if target_channel_name in ch.get("name", "").lower():
                        return {
                            "channel_id": str(ch["id"]),
                            "channel_name": f"#{ch.get('name')}",
                            "guild_id": str(g_id),
                            "guild_name": g_name,
                        }

            # Prioritize standard general channel names
            preferred_names = ["general", "main", "chat", "lounge", "discussion", "talk"]
            for pref in preferred_names:
                for ch in text_channels:
                    if pref in ch.get("name", "").lower():
                        return {
                            "channel_id": str(ch["id"]),
                            "channel_name": f"#{ch.get('name')}",
                            "guild_id": str(g_id),
                            "guild_name": g_name,
                        }

            if text_channels:
                ch = text_channels[0]
                return {
                    "channel_id": str(ch["id"]),
                    "channel_name": f"#{ch.get('name')}",
                    "guild_id": str(g_id),
                    "guild_name": g_name,
                }

        # 4. Search across all guilds for matching channel name
        matches = await self.search_channels(query=clean)
        if matches:
            return matches[0]

        return None

    async def fetch_relationships(self) -> List[Dict[str, Any]]:
        """Fetches user account's friends and DM relationships."""
        url = f"{self.base_url}/users/@me/relationships"
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"[DiscordRestClient] fetch_relationships error: {e}")
        return []

    async def search_guild_members(
        self, guild_id: str, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Searches for members within a guild by username or nickname."""
        import urllib.parse
        q = urllib.parse.quote(query)
        url = f"{self.base_url}/guilds/{guild_id}/members/search?query={q}&limit={limit}"
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"[DiscordRestClient] search_guild_members error: {e}")
        return []

    async def resolve_user(
        self, query: str, guild_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Finds user ID and mention tag by username, global_name, or nickname."""
        clean = query.strip().lstrip("@").lower()

        # 1. Search relationships / friends
        friends = await self.fetch_relationships()
        for rel in friends:
            u = rel.get("user", {})
            if clean in (u.get("username", "").lower(), (u.get("global_name") or "").lower()):
                return {
                    "user_id": str(u["id"]),
                    "username": u.get("username"),
                    "display_name": u.get("global_name") or u.get("username"),
                    "mention": f"<@{u['id']}>",
                }

        # 2. Search guild members if guild_id provided
        if guild_id:
            members = await self.search_guild_members(guild_id=guild_id, query=clean, limit=5)
            for m in members:
                u = m.get("user", {})
                nick = (m.get("nick") or "").lower()
                if clean in (u.get("username", "").lower(), (u.get("global_name") or "").lower(), nick):
                    return {
                        "user_id": str(u["id"]),
                        "username": u.get("username"),
                        "display_name": m.get("nick") or u.get("global_name") or u.get("username"),
                        "mention": f"<@{u['id']}>",
                    }
        return None

    async def get_or_create_dm_channel(self, recipient_id: str) -> Optional[str]:
        """Gets or opens a 1-on-1 Direct Message channel with a user."""
        url = f"{self.base_url}/users/@me/channels"
        session = await self._get_session()
        payload = {"recipients": [str(recipient_id)]}
        try:
            async with session.post(url, json=payload) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    return str(data.get("id"))
                elif resp.status == 400:
                    async with session.post(url, json={"recipient_id": str(recipient_id)}) as resp2:
                        if resp2.status in (200, 201):
                            data2 = await resp2.json()
                            return str(data2.get("id"))
        except Exception as e:
            logger.error(f"[DiscordRestClient] get_or_create_dm_channel error: {e}")
        return None

    async def send_dm(
        self,
        recipient_id: str,
        content: str,
        file_path: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Sends a Direct Message to a user by their user ID."""
        dm_channel_id = await self.get_or_create_dm_channel(recipient_id)
        if not dm_channel_id:
            return None
        return await self.send_message(
            channel_id=dm_channel_id,
            content=content,
            file_path=file_path,
            file_bytes=file_bytes,
            filename=filename,
        )

    async def fetch_dm_channels(self) -> List[Dict[str, Any]]:
        """Retrieves all active DM and Group DM channels."""
        url = f"{self.base_url}/users/@me/channels"
        session = await self._get_session()
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.error(f"[DiscordRestClient] fetch_dm_channels error: {e}")
        return []

