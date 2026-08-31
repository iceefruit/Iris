from typing import Any, Dict, List
from integrations.discord.emojis import emoji_registry, DEFAULT_CUSTOM_EMOJIS


class DiscordMessageFormatter:
    """Formats Iris execution events and LLM outputs for Discord with custom aesthetic emojis."""

    def __init__(self):
        self.emojis = emoji_registry

    @staticmethod
    def chunk_message(text: str, max_length: int = 1900) -> List[str]:
        """Splits long text into Discord-safe chunks while preserving markdown codeblock tags."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        lines = text.split("\n")
        current_chunk = []
        current_len = 0
        in_codeblock = False
        codeblock_lang = ""

        for line in lines:
            if line.strip().startswith("```"):
                if not in_codeblock:
                    in_codeblock = True
                    codeblock_lang = line.strip()[3:].strip()
                else:
                    in_codeblock = False
                    codeblock_lang = ""

            while len(line) > max_length:
                part = line[:max_length]
                line = line[max_length:]
                if current_chunk:
                    if in_codeblock:
                        current_chunk.append("```")
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [f"```{codeblock_lang}"] if in_codeblock else []
                    current_len = len(current_chunk[0]) if current_chunk else 0
                chunks.append(part)

            if not line and not current_chunk:
                continue

            if current_len + len(line) + 1 > max_length:
                if in_codeblock:
                    current_chunk.append("```")
                chunks.append("\n".join(current_chunk))
                current_chunk = [f"```{codeblock_lang}", line] if in_codeblock else [line]
                current_len = sum(len(l) for l in current_chunk) + len(current_chunk)
            else:
                current_chunk.append(line)
                current_len += len(line) + 1

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    @staticmethod
    def format_user_mentions(text: str, user_mapping: Dict[str, str]) -> str:
        """Replaces @username in outgoing text with Discord mention <@user_id>."""
        import re
        for username, user_id in user_mapping.items():
            pattern = rf"@\b{re.escape(username.lstrip('@'))}\b"
            text = re.sub(pattern, f"<@{user_id}>", text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def parse_mentions_to_readable(text: str, user_cache: Dict[str, str]) -> str:
        """Converts <@123456789> into @Username for cleaner LLM ingestion."""
        import re
        def _replace_id(m: re.Match) -> str:
            uid = m.group(1)
            return f"@{user_cache.get(uid, f'User_{uid}')}"
        return re.sub(r"<@!?([0-9]+)>", _replace_id, text)

    def format_intent_badge(self, category: str, query: str) -> str:
        arrow_anim = self.emojis.get("8r_arrow", "<a:8R_arrow:1280406522190495884>")
        white_arrow = self.emojis.get("white_arrow", "<:white_arrow:1527313231868329994>")
        flower = self.emojis.get("ea_flower", "<:ea_flower:1541018931823644732>")
        heart = self.emojis.get("heart_3_", "<a:heart_3_:1285903837340762185>")
        bow = self.emojis.get("white_bow", "<:white_bow:1527313288235581470>")
        star = self.emojis.get("02_black_star", "<:02_Black_Star:1541019032566767616>")
        sparkle = self.emojis.get("emoji_024", "<:emoji_024:1541018951926947850>")

        icons = {
            "GOAL": f"{arrow_anim} {star} **[Autonomous Goal Mode]**",
            "ACTION": f"{white_arrow} {sparkle} **[Desktop Action Mode]**",
            "VISION": f"{flower} **[Screen Vision Mode]**",
            "MEMORY": f"{heart} **[Knowledge Vault Mode]**",
            "CHAT": f"{bow} **[Conversational Mode]**",
        }
        icon = icons.get(category, f"{bow} **[Iris Processing]**")
        return f"{icon} *\"{query}\"*"

    def format_action_call(self, tool: str, arguments: Dict[str, Any]) -> str:
        white_arrow = self.emojis.get("white_arrow", "<:white_arrow:1527313231868329994>")
        args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
        return f"{white_arrow} `Executing Action:` **{tool}**({args_str})"

    def format_action_result(self, tool: str, result: str, success: bool = True) -> str:
        sparkle = self.emojis.get("emoji_024", "<:emoji_024:1541018951926947850>")
        sad = self.emojis.get("kittysad", "<:KittySad:1268275441580376074>")
        status_icon = sparkle if success else sad
        # Truncate long result outputs
        short_res = result[:300] + ("..." if len(result) > 300 else "")
        return f"{status_icon} `{tool} Result:` {short_res}"

    def format_vision_context(self, app: str, title: str) -> str:
        flower = self.emojis.get("ea_flower", "<:ea_flower:1541018931823644732>")
        return f"{flower} `Active App:` **{app}** | *{title[:50]}*"

    def format_goal_completed(self, summary: str) -> str:
        heart = self.emojis.get("heart_3_", "<a:heart_3_:1285903837340762185>")
        crown = self.emojis.get("crown_white_neon", "<:crown_white_neon:1273239112631058524>")
        return f"{heart} {crown} **Goal Completed:** {summary}"

    def format_goal_aborted(self, reason: str) -> str:
        sad = self.emojis.get("kittysad", "<:KittySad:1268275441580376074>")
        return f"{sad} **Goal Aborted:** {reason}"

    def format_ai_content(self, text: str) -> str:
        """Applies dynamic emoji replacements to AI-generated text."""
        return self.emojis.format_text(text)
