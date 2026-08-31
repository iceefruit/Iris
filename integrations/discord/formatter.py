"""Discord Message Formatter for Iris Autonomous Responses."""

from typing import Any, Dict, List


class DiscordMessageFormatter:
    """Formats Iris execution events and LLM outputs for Discord."""

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

    @staticmethod
    def format_intent_badge(category: str, query: str) -> str:
        icons = {
            "GOAL": "🚀 **[Autonomous Goal Mode]**",
            "ACTION": "⚡ **[Desktop Action Mode]**",
            "VISION": "📸 **[Screen Vision Mode]**",
            "MEMORY": "🧠 **[Knowledge Vault Mode]**",
            "CHAT": "💬 **[Conversational Mode]**",
        }
        icon = icons.get(category, "✨ **[Iris Processing]**")
        return f"{icon} *\"{query}\"*"

    @staticmethod
    def format_action_call(tool: str, arguments: Dict[str, Any]) -> str:
        args_str = ", ".join(f"{k}={v}" for k, v in arguments.items())
        return f"⚡ `Executing Action:` **{tool}**({args_str})"

    @staticmethod
    def format_action_result(tool: str, result: str, success: bool = True) -> str:
        status_icon = "✔" if success else "❌"
        # Truncate long result outputs
        short_res = result[:300] + ("..." if len(result) > 300 else "")
        return f"{status_icon} `{tool} Result:` {short_res}"

    @staticmethod
    def format_vision_context(app: str, title: str) -> str:
        return f"📸 `Active App:` **{app}** | *{title[:50]}*"

    @staticmethod
    def format_goal_completed(summary: str) -> str:
        return f"🎉 **Goal Completed:** {summary}"

    @staticmethod
    def format_goal_aborted(reason: str) -> str:
        return f"🛑 **Goal Aborted:** {reason}"
