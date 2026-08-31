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
        """Sends the user turn to Miko API and streams back chunk events.
        
        Miko API maintains conversational context on the server side using
        (username, userid). Thus, we send only the new prompt message to the API,
        while maintaining local memory for display and logging.
        """
        # Store in local history
        self.memory.add_message(role="user", content=user_input)

        # Upload files if provided
        server_files = None
        if file_paths:
            server_files = self.client.upload_files(file_paths)

        # Send only the new user message to Miko API as per Miko docs specification
        messages_payload = [{"role": "user", "content": user_input}]

        full_response_accumulator = []

        try:
            for chunk in self.client.stream_chat(
                messages=messages_payload,
                service=config.service,
                search=config.search,
                thinking=config.thinking,
                system_prompt=config.system_prompt,
                files=server_files,
            ):
                if chunk.chunk_type == "content":
                    full_response_accumulator.append(chunk.text)
                yield chunk

            # Store completed turn into local memory
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
        """Clears both local context window and Miko server-side session memory."""
        self.memory.clear()
        return self.client.clear_history()
