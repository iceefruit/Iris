"""Discord File and Message Dispatch Tool for Iris."""

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, Optional
from config import config
from tools.base import BaseTool, ToolResult


class SendDiscordFileTool(BaseTool):
    """Sends a local file, screenshot, or report to a Discord channel via the Discord REST client."""

    def __init__(self, rest_client: Optional[Any] = None):
        self.rest_client = rest_client

    @property
    def name(self) -> str:
        return "send_discord_file"

    @property
    def description(self) -> str:
        return (
            "Uploads and sends a local file, image, or screenshot to a specified Discord channel or DM. "
            "Use this when requested to send a file to Discord."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channel_id": {
                    "type": "string",
                    "description": "Discord channel or DM ID to send the file to.",
                },
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the local file to upload.",
                },
                "caption": {
                    "type": "string",
                    "description": "Optional text message/caption to accompany the file.",
                },
            },
            "required": ["channel_id", "file_path"],
        }

    def execute(self, channel_id: str, file_path: str, caption: str = "") -> ToolResult:
        if not file_path or not Path(file_path).exists():
            return ToolResult(
                success=False,
                output="",
                error=f"File not found: '{file_path}'",
            )

        token = getattr(config, "discord_user_token", "")
        if not token:
            return ToolResult(
                success=False,
                output="",
                error="No DISCORD_USER_TOKEN configured in settings.",
            )

        from integrations.discord.client import DiscordRestClient
        client = self.rest_client or DiscordRestClient(token=token)

        async def _upload():
            return await client.send_message(
                channel_id=channel_id,
                content=caption,
                file_path=file_path,
            )

        try:
            res = asyncio.run(_upload())
            if res and "id" in res:
                return ToolResult(
                    success=True,
                    output=f"Successfully sent file '{os.path.basename(file_path)}' to Discord channel {channel_id} (Message ID: {res['id']})",
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error="Discord API failed to upload file.",
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Discord upload error: {str(e)}",
            )
