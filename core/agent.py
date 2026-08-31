"""Central Agent coordinator for Iris."""

from typing import Generator, List, Optional
from core.protocols import LLMClientProtocol, MemoryProtocol, StreamChunk
from config import config


class IrisAgent:
    def __init__(self, client: LLMClientProtocol, memory: MemoryProtocol):
        self.client = client
        self.memory = memory

    def ask(
        self, user_input: str, file_paths: Optional[List[str]] = None
    ) -> Generator[StreamChunk, None, None]:
        """Ingests user input, queries Miko API, streams chunks, and updates context."""
        self.memory.add_message(role="user", content=user_input)
        context = self.memory.get_context()

        # Handle file uploads if requested
        server_files = None
        if file_paths:
            server_files = self.client.upload_files(file_paths)

        full_response_accumulator = []

        try:
            for chunk in self.client.stream_chat(
                messages=context,
                service=config.service,
                search=config.search,
                thinking=config.thinking,
                system_prompt=config.system_prompt,
                files=server_files,
            ):
                if chunk.chunk_type == "content":
                    full_response_accumulator.append(chunk.text)
                yield chunk

            # Store the assistant turn in memory
            full_response = "".join(full_response_accumulator)
            if full_response:
                self.memory.add_message(role="assistant", content=full_response)

        except Exception as e:
            error_chunk = StreamChunk(
                chunk_type="error",
                text=f"\n[Error communicating with Miko API: {str(e)}]"
            )
            yield error_chunk

    def clear(self) -> bool:
        """Clears both local context window and server-side session memory."""
        self.memory.clear()
        return self.client.clear_history()
