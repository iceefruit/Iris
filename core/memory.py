"""In-memory sliding window conversation context manager."""

from typing import List, Dict
from core.protocols import Message, MemoryProtocol


class ConversationMemory(MemoryProtocol):
    def __init__(self, system_prompt: str, max_messages: int = 20):
        self.system_prompt = system_prompt
        self.max_messages = max(2, max_messages)  # Ensure at least 1 roundtrip
        self._history: List[Message] = []

    def add_message(self, role: str, content: str) -> None:
        self._history.append(Message(role=role, content=content))
        self._trim()

    def _trim(self) -> None:
        """Keeps recent messages within the sliding window limit."""
        if len(self._history) > self.max_messages:
            # Preserve recent conversation without truncating mid-turn
            self._history = self._history[-self.max_messages:]

    def get_context(self) -> List[Dict[str, str]]:
        """Compiles system prompt and active message history."""
        context = [{"role": "system", "content": self.system_prompt}]
        context.extend([msg.to_dict() for msg in self._history])
        return context

    def clear(self) -> None:
        self._history.clear()

    @property
    def message_count(self) -> int:
        return len(self._history)
