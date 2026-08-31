"""Low-latency streaming client for OpenAI-compatible APIs (Miko Yokoya)."""

import json
import httpx
from typing import Generator, List, Dict, Optional
from core.protocols import LLMClientProtocol


class MikoClient(LLMClientProtocol):
    def __init__(self, base_url: str, api_key: str, default_model: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = 0.7,
    ) -> Generator[str, None, None]:
        """Streams text chunks from the OpenAI-compatible completions endpoint."""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", url, headers=self._headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = response.read().decode("utf-8", errors="replace")
                    raise RuntimeError(
                        f"API Request Failed [{response.status_code}]: {error_text}"
                    )

                for line in response.iter_lines():
                    if not line:
                        continue

                    line = line.strip()
                    if line.startswith("data:"):
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if not choices:
                                continue

                            delta = choices[0].get("delta", {})
                            content_chunk = delta.get("content")
                            if content_chunk:
                                yield content_chunk
                        except json.JSONDecodeError:
                            continue
