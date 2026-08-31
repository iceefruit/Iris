"""Custom Discord Emoji Registry & Dynamic Server Emoji Fetcher for Iris."""

import logging
import re
from typing import Any, Dict, List, Optional
import aiohttp

logger = logging.getLogger("Iris_DiscordEmojis")

# Pre-configured user custom server emojis
DEFAULT_CUSTOM_EMOJIS: Dict[str, str] = {
    # Arrows & Pointers
    "white_arrow": "<:white_arrow:1527313231868329994>",
    "arrow": "<:white_arrow:1527313231868329994>",
    "8r_arrow": "<a:8R_arrow:1280406522190495884>",
    "animated_arrow": "<a:8R_arrow:1280406522190495884>",

    # Hearts & Cute
    "heart_3_": "<a:heart_3_:1285903837340762185>",
    "heart_3": "<a:heart_3_:1285903837340762185>",
    "heart": "<a:heart_3_:1285903837340762185>",
    "01redhearts": "<:01redhearts:1541018979986968608>",
    "red_hearts": "<:01redhearts:1541018979986968608>",

    # Aesthetics & Crowns & Stars
    "white_bow": "<:white_bow:1527313288235581470>",
    "bow": "<:white_bow:1527313288235581470>",
    "crown_white_neon": "<:crown_white_neon:1273239112631058524>",
    "crown": "<:crown_white_neon:1273239112631058524>",
    "ea_flower": "<:ea_flower:1541018931823644732>",
    "flower": "<:ea_flower:1541018931823644732>",
    "emoji_024": "<:emoji_024:1541018951926947850>",
    "sparkle": "<:emoji_024:1541018951926947850>",
    "02_black_star": "<:02_Black_Star:1541019032566767616>",
    "black_star": "<:02_Black_Star:1541019032566767616>",
    "star": "<:02_Black_Star:1541019032566767616>",

    # Expressions
    "kittysad": "<:KittySad:1268275441580376074>",
    "catsad_uwu": "<:catsad_UwU:1186551897419681822>",
    "catsad": "<:catsad_UwU:1186551897419681822>",
    "emoji_107": "<:emoji_107:1215238922951720970>",
    "invis": "<:invis:1533059523399385229>",
}


class EmojiRegistry:
    """Manages custom server emojis and replaces text tags with Discord emojis."""

    def __init__(self):
        self._emojis: Dict[str, str] = dict(DEFAULT_CUSTOM_EMOJIS)

    def register_emoji(self, name: str, emoji_code: str):
        """Registers a custom emoji name -> <a:name:id> code."""
        clean_name = name.strip(":").lower()
        self._emojis[clean_name] = emoji_code

    def get(self, name: str, fallback: str = "") -> str:
        """Retrieves formatted emoji string by name."""
        clean_name = name.strip(":").lower()
        return self._emojis.get(clean_name, fallback)

    def list_emojis(self) -> Dict[str, str]:
        """Returns all registered custom emojis."""
        return dict(self._emojis)

    def format_text(self, text: str) -> str:
        """Replaces colon-wrapped names (:flower:, :crown:, etc.) with Discord emoji codes."""
        if not text:
            return ""

        def _replace_match(m: re.Match) -> str:
            raw_key = m.group(1).lower()
            return self._emojis.get(raw_key, m.group(0))

        # Matches :word_name:
        pattern = r":([a-zA-Z0-9_\-]+):"
        return re.sub(pattern, _replace_match, text)

    async def fetch_user_guild_emojis(self, token: str, session: Optional[aiohttp.ClientSession] = None):
        """Dynamically fetches all accessible custom emojis across the user account's servers."""
        if not token:
            return

        headers = {
            "Authorization": token,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) discord/1.0.9171 Chrome/128.0.6613.186 Electron/32.2.6 Safari/537.36"
            ),
        }

        should_close = False
        if session is None:
            session = aiohttp.ClientSession(headers=headers)
            should_close = True

        try:
            # 1. Fetch user's guilds
            async with session.get("https://discord.com/api/v9/users/@me/guilds?limit=100") as resp:
                if resp.status != 200:
                    return
                guilds = await resp.json()

            count = 0
            for g in guilds[:25]:  # Query up to 25 guilds
                gid = g.get("id")
                if not gid:
                    continue
                try:
                    async with session.get(f"https://discord.com/api/v9/guilds/{gid}?with_counts=false") as g_resp:
                        if g_resp.status == 200:
                            g_data = await g_resp.json()
                            emojis = g_data.get("emojis", [])
                            for e in emojis:
                                ename = e.get("name", "").lower()
                                eid = e.get("id")
                                is_animated = e.get("animated", False)
                                prefix = "a" if is_animated else ""
                                formatted_code = f"<{prefix}:{e.get('name')}:{eid}>"
                                if ename and eid:
                                    self._emojis[ename] = formatted_code
                                    count += 1
                except Exception:
                    continue

            logger.info(f"[EmojiRegistry] Discovered and registered {count} custom Discord emojis.")

        except Exception as e:
            logger.warning(f"[EmojiRegistry] Failed to fetch server emojis: {e}")
        finally:
            if should_close:
                await session.close()


# Shared singleton registry
emoji_registry = EmojiRegistry()
