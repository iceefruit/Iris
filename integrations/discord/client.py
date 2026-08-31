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
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

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
