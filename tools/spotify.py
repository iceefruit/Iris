"""Spotify Music Player & Media Control Tool for Iris."""

import os
import subprocess
import time
import urllib.parse
from typing import Any, Dict, Optional
import pyautogui

from tools.base import BaseTool, ToolResult


class SpotifyTool(BaseTool):
    """Controls Spotify playback, searches tracks/artists/albums, and dispatches media actions."""

    @property
    def name(self) -> str:
        return "spotify_control"

    @property
    def description(self) -> str:
        return (
            "Controls Spotify playback and searches music on Spotify. "
            "Use this when the user asks to play a song/artist (e.g. 'play michael jackson'), "
            "pause/resume music, skip to the next/previous song, or search music on Spotify."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["play", "search", "pause", "resume", "play_pause", "next", "previous"],
                    "description": "The playback or search action to perform.",
                },
                "query": {
                    "type": "string",
                    "description": "The song title, artist name, album, or playlist to search/play (e.g. 'Michael Jackson', 'Blinding Lights', 'Lofi Beats').",
                },
                "entity_type": {
                    "type": "string",
                    "enum": ["track", "artist", "album", "playlist", "all"],
                    "description": "Optional category to refine search (default: 'all').",
                },
            },
            "required": ["action"],
        }

    def execute(
        self,
        action: str,
        query: Optional[str] = None,
        entity_type: str = "all",
    ) -> ToolResult:
        act = action.lower().strip()

        # Handle simple media playback actions
        if act in ("pause", "resume", "play_pause"):
            pyautogui.press("playpause")
            return ToolResult(
                success=True,
                output="Toggled media playback (Play/Pause).",
            )

        if act == "next":
            pyautogui.press("nexttrack")
            return ToolResult(
                success=True,
                output="Skipped to next track.",
            )

        if act == "previous":
            pyautogui.press("prevtrack")
            return ToolResult(
                success=True,
                output="Returned to previous track.",
            )

        # Handle search & play queries
        if act in ("play", "search"):
            if not query:
                # If play requested without query, simply resume playback
                pyautogui.press("playpause")
                return ToolResult(
                    success=True,
                    output="Resumed playback.",
                )

            clean_query = query.strip()
            # Encode for Spotify URI
            encoded_query = urllib.parse.quote(clean_query)
            spotify_uri = f"spotify:search:{encoded_query}"

            try:
                # Launch Spotify URI via Windows shell
                os.startfile(spotify_uri)
                time.sleep(0.8)

                # If action is 'play', simulate Enter key to automatically trigger first search result
                if act == "play":
                    time.sleep(0.4)
                    pyautogui.press("enter")
                    time.sleep(0.3)
                    pyautogui.press("space")

                return ToolResult(
                    success=True,
                    output=f"Searched and launched Spotify for '{clean_query}'. Playing on Spotify.",
                )
            except Exception as e:
                # Fallback to browser Web Player if desktop app URI handler is unavailable
                web_url = f"https://open.spotify.com/search/{encoded_query}"
                try:
                    os.startfile(web_url)
                    return ToolResult(
                        success=True,
                        output=f"Opened Spotify Web Player for '{clean_query}' at {web_url}.",
                    )
                except Exception as ex:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to launch Spotify: {str(e)} / {str(ex)}",
                    )

        return ToolResult(
            success=False,
            output="",
            error=f"Unknown Spotify action: '{action}'.",
        )
