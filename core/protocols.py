"""Abstract interfaces and protocol contracts for Iris."""

from typing import Protocol, List, Dict, Any, Generator, Optional
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # 'system' | 'user' | 'assistant'
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class MemoryProtocol(Protocol):
    """Contract for managing conversation context."""

    def add_message(self, role: str, content: str) -> None:
        ...

    def get_context(self) -> List[Dict[str, str]]:
        ...

    def clear(self) -> None:
        ...


class LLMClientProtocol(Protocol):
    """Contract for LLM communication."""

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Generator[str, None, None]:
        ...
