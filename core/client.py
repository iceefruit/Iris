import json
import threading
import time
import httpx
from typing import Generator, List, Dict, Any, Optional
from core.protocols import LLMClientProtocol, StreamChunk
from config import config


class MikoClient(LLMClientProtocol):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        default_service: str = "qwen-max",
        username: str = "iris_user",
        userid: str = "iris_local_1",
        timeout: float = 60.0,
        max_requests_per_second: Optional[float] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_service = default_service
        self.username = username
        self.userid = userid
        self.timeout = timeout
        self.max_rps = max_requests_per_second or getattr(config, "max_requests_per_second", 2.0)
        self._min_interval = 1.0 / max(0.1, self.max_rps)
        self._last_request_time = 0.0
        self._rate_lock = threading.Lock()
        self._headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _throttle(self) -> None:
        """Enforces client-side rate limiting so requests do not exceed max RPS."""
        with self._rate_lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                sleep_needed = self._min_interval - elapsed
                time.sleep(sleep_needed)
            self._last_request_time = time.time()

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        service: Optional[str] = None,
        search: bool = True,
        thinking: bool = False,
        system_prompt: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> Generator[StreamChunk, None, None]:
        """Streams real-time events from Miko /chat endpoint."""
        self._throttle()
        url = f"{self.base_url}/chat"
        payload: Dict[str, Any] = {
            "service": service or self.default_service,
            "messages": messages,
            "username": self.username,
            "userid": self.userid,
            "search": search,
            "thinking": thinking,
            "stream": True,
        }
        if system_prompt:
            payload["system_prompt"] = system_prompt
        if files:
            payload["files"] = files

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", url, headers=self._headers, json=payload) as response:
                if response.status_code != 200:
                    error_body = response.read().decode("utf-8", errors="replace")
                    raise RuntimeError(
                        f"Miko API Error [{response.status_code}]: {error_body}"
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
                            chunk_type = data.get("type", "content")

                            if chunk_type == "content":
                                content = data.get("content", "")
                                if content:
                                    yield StreamChunk(chunk_type="content", text=content)

                            elif chunk_type == "thinking":
                                reasoning = data.get("content", "")
                                if reasoning:
                                    yield StreamChunk(chunk_type="thinking", text=reasoning)

                            elif chunk_type == "function_call":
                                call_info = data.get("call") or data.get("content") or json.dumps(data)
                                yield StreamChunk(
                                    chunk_type="function_call",
                                    text=str(call_info),
                                    metadata=data
                                )

                            elif chunk_type == "function_result":
                                res_info = data.get("result") or data.get("content") or ""
                                yield StreamChunk(
                                    chunk_type="function_result",
                                    text=str(res_info),
                                    metadata=data
                                )

                            elif chunk_type == "final":
                                yield StreamChunk(
                                    chunk_type="final",
                                    text="",
                                    metadata=data.get("data") or data
                                )

                            elif chunk_type == "error":
                                error_msg = data.get("content") or str(data)
                                yield StreamChunk(chunk_type="error", text=error_msg)

                        except json.JSONDecodeError:
                            continue

    def clear_history(self) -> bool:
        """Clears server-side conversation history for this session."""
        self._throttle()
        url = f"{self.base_url}/clear-history"
        payload = {
            "username": self.username,
            "userid": self.userid,
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=self._headers, json=payload)
                return res.status_code == 200
        except Exception:
            return False

    def upload_files(self, file_paths: List[str]) -> List[str]:
        """Uploads local files to Miko and returns temporary server paths."""
        self._throttle()
        url = f"{self.base_url}/upload-files"
        headers = {"X-API-Key": self.api_key}

        files_to_send = []
        file_handles = []
        try:
            for path in file_paths:
                f = open(path, "rb")
                file_handles.append(f)
                files_to_send.append(("files", f))

            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, headers=headers, files=files_to_send)
                if res.status_code == 200:
                    data = res.json()
                    return data.get("files", [])
                else:
                    raise RuntimeError(f"File upload failed [{res.status_code}]: {res.text}")
        finally:
            for f in file_handles:
                f.close()

    def generate_image(
        self, prompt: str, size: str = "16:9", model: str = "qwen-image-2"
    ) -> List[Dict[str, Any]]:
        """Generates images using Miko /image endpoint."""
        self._throttle()
        url = f"{self.base_url}/image"
        payload = {
            "prompt": prompt,
            "model": model,
            "size": size,
            "username": self.username,
            "userid": self.userid,
        }
        with httpx.Client(timeout=self.timeout) as client:
            res = client.post(url, headers=self._headers, json=payload)
            if res.status_code == 200:
                data = res.json()
                return data.get("images", [])
            else:
                raise RuntimeError(f"Image generation failed [{res.status_code}]: {res.text}")

