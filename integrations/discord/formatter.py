from typing import Any, Dict, List
from integrations.discord.emojis import emoji_registry, DEFAULT_CUSTOM_EMOJIS


class DiscordMessageFormatter:
    """Formats Iris execution events and LLM outputs for Discord with custom aesthetic emojis."""

    def __init__(self):
        self.emojis = emoji_registry

    @staticmethod
    def chunk_message(text: str, max_length: int = 1900) -> List[str]:
        """Splits long text into Discord-safe message chunks."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        lines = text.split("\n")
        current_chunk = []
        current_len = 0

        for line in lines:
            # If a single line itself exceeds max_length, slice it
            while len(line) > max_length:
                part = line[:max_length]
                line = line[max_length:]
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                chunks.append(part)

            if not line:
                continue

            if current_len + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = len(line)
            else:
                current_chunk.append(line)
                current_len += len(line) + 1

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

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
