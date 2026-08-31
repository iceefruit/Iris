"""Central Agent coordinator for Iris."""

from typing import Generator
from core.protocols import LLMClientProtocol, MemoryProtocol
from config import config


class IrisAgent:
    def __init__(self, client: LLMClientProtocol, memory: MemoryProtocol):
        self.client = client
        self.memory = memory

    def ask(self, user_input: str) -> Generator[str, None, None]:
        """Ingests user input, queries the LLM with context, streams response, and saves memory."""
        self.memory.add_message(role="user", content=user_input)
        context = self.memory.get_context()

        full_response_accumulator = []

        try:
            for chunk in self.client.stream_chat(
                messages=context,
                model=config.model,
                temperature=config.temperature
            ):
                full_response_accumulator.append(chunk)
                yield chunk

            # Store the complete assistant turn in memory
            full_response = "".join(full_response_accumulator)
            self.memory.add_message(role="assistant", content=full_response)

        except Exception as e:
            # Yield error description and abort turn gracefully
            error_msg = f"\n[Error communicating with model: {str(e)}]"
            yield error_msg
