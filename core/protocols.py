"""Abstract interfaces and protocol contracts for Iris."""

from typing import Protocol, List, Dict, Any, Generator, Optional
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # 'user' | 'assistant'
    content: str

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class StreamChunk:
    chunk_type: str  # 'content' | 'thinking' | 'function_call' | 'function_result' | 'final' | 'error'
    text: str
    metadata: Optional[Dict[str, Any]] = None


class MemoryProtocol(Protocol):
    """Contract for local session tracking."""

    def add_message(self, role: str, content: str) -> None:
        ...

    def get_context(self) -> List[Dict[str, str]]:
        ...

    def clear(self) -> None:
        ...


class LLMClientProtocol(Protocol):
    """Contract for Miko API communication."""

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        service: Optional[str] = None,
        search: bool = True,
        thinking: bool = False,
        system_prompt: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> Generator[StreamChunk, None, None]:
        ...

    def clear_history(self) -> bool:
        ...

    def upload_files(self, file_paths: List[str]) -> List[str]:
        ...

    def generate_image(
        self, prompt: str, size: str = "16:9", model: str = "qwen-image-2"
    ) -> List[Dict[str, Any]]:
        ...
