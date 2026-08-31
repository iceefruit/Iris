"""Discord WebSocket Gateway Client for User Account Authentication."""

import asyncio
import json
import logging
from typing import Callable, Dict, Optional
import websockets

logger = logging.getLogger("Iris_DiscordGateway")


class DiscordGateway:
    """Connects to Discord Gateway WebSocket as a user account and listens for events."""

    def __init__(
        self,
        token: str,
        on_message_callback: Optional[Callable[[Dict], None]] = None,
    ):
        self.token = token.strip().strip('"').strip("'")
        self.on_message_callback = on_message_callback
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.user: Optional[Dict] = None
        self.session_id: Optional[str] = None
        self.seq_num: Optional[int] = None
        self.resume_gateway_url: Optional[str] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._is_running = False
        self.is_valid_token = True

    async def connect(self, max_retries: int = 5):
        """Connects to Discord WebSocket gateway with exponential backoff."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        base = self.resume_gateway_url if self.resume_gateway_url else "wss://gateway.discord.gg"
        sep = "&" if "?" in base else "?"
        url = f"{base}{sep}encoding=json&v=10"

        backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                self.ws = await websockets.connect(
                    url,
                    max_size=50_000_000,
                    ping_interval=None,
                )
                return
            except Exception as e:
                logger.warning(f"[DiscordGateway] Connection attempt {attempt}/{max_retries} failed: {e}")
                if attempt == max_retries:
                    raise
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, 30.0)

    async def send_json(self, payload: dict) -> bool:
        """Sends JSON payload to the Discord gateway."""
        try:
            if self.ws is not None:
                await self.ws.send(json.dumps(payload))
                await asyncio.sleep(0.05)
                return True
        except Exception:
            pass
        return False

    async def recv_json(self) -> Optional[Dict]:
        """Receives and parses JSON from the Discord gateway."""
        try:
            if self.ws is None:
                return None
            item = await self.ws.recv()
            data = json.loads(item)
            if data.get("s") is not None:
                self.seq_num = data["s"]
            return data
        except websockets.exceptions.ConnectionClosed as e:
            if e.code in (4004, 4010, 4011, 4012, 4013, 4014):
                logger.error(f"[DiscordGateway] Fatal Auth/Intent Error ({e.code}): Invalid or disabled token.")
                self.is_valid_token = False
            else:
                logger.info(f"[DiscordGateway] Gateway closed: code={e.code}")
            return None
        except Exception:
            return None

    async def _heartbeat_loop(self, interval: float):
        """Maintains gateway heartbeat connection."""
        try:
            while self._is_running:
                await asyncio.sleep(interval)
                success = await self.send_json({"op": 1, "d": self.seq_num})
                if not success:
                    break
        except asyncio.CancelledError:
            pass

    async def identify(self):
        """Sends Opcode 2 Identify payload."""
        await self.send_json({
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {
                    "$os": "Windows",
                    "$browser": "Discord Client",
                    "$device": "",
                    "$system_locale": "en-US",
                    "$browser_user_agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) discord/1.0.9171 Chrome/128.0.6613.186 Electron/32.2.6 Safari/537.36"
                    ),
                    "$browser_version": "32.2.6",
                    "$os_version": "10",
                    "$release_channel": "stable",
                    "$client_build_number": 361734,
                },
                "compress": False,
                "capabilities": 30717,
            },
        })

    async def resume(self):
        """Sends Opcode 6 Resume payload."""
        await self.send_json({
            "op": 6,
            "d": {
                "token": self.token,
                "session_id": self.session_id,
                "seq": self.seq_num,
            },
        })

    async def run(self):
        """Main connection and event processing loop."""
        self._loop = asyncio.get_running_loop()
        self._is_running = True
        while self._is_running and self.is_valid_token:
            try:
                await self.connect()
                hello_data = await self.recv_json()
                if not hello_data or "d" not in hello_data:
                    await asyncio.sleep(3.0)
                    continue

                interval = hello_data["d"].get("heartbeat_interval", 41250) / 1000.0
                if self._heartbeat_task and not self._heartbeat_task.done():
                    self._heartbeat_task.cancel()
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(interval))

                if self.session_id and self.seq_num:
                    await self.resume()
                else:
                    await self.identify()

                while self._is_running:
                    event = await self.recv_json()
                    if event is None:
                        break

                    op = event.get("op")
                    t = event.get("t")
                    d = event.get("d", {})

                    if t == "READY":
                        self.user = d.get("user")
                        self.session_id = d.get("session_id")
                        self.resume_gateway_url = d.get("resume_gateway_url")
                        logger.info(
                            f"[DiscordGateway] Successfully Logged in as: "
                            f"{self.user.get('username', 'Unknown')}#{self.user.get('discriminator', '0000')} "
                            f"(ID: {self.user.get('id', '')})"
                        )

                    elif t == "RESUMED":
                        logger.info("[DiscordGateway] Session successfully resumed.")

                    elif t == "MESSAGE_CREATE":
                        if self.on_message_callback:
                            d["_gateway_user_id"] = self.user.get("id", "") if self.user else ""
                            d["_gateway_token"] = self.token
                            try:
                                if asyncio.iscoroutinefunction(self.on_message_callback):
                                    asyncio.create_task(self.on_message_callback(d))
                                else:
                                    self.on_message_callback(d)
                            except Exception as e:
                                logger.error(f"[DiscordGateway] Callback execution error: {e}")

                    elif op == 7:  # Reconnect
                        logger.info("[DiscordGateway] Reconnect requested by Discord.")
                        break

                    elif op == 9:  # Invalid session
                        logger.warning("[DiscordGateway] Invalid session (Op 9).")
                        self.session_id = None
                        self.seq_num = None
                        break

            except asyncio.CancelledError:
                break
            except Exception as err:
                logger.error(f"[DiscordGateway] Error: {err}")

            if self._is_running and self.is_valid_token:
                await asyncio.sleep(5.0)

    def stop(self):
        """Stops the gateway connection."""
        self._is_running = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        if self.ws:
            if hasattr(self, "_loop") and self._loop and self._loop.is_running():
                try:
                    asyncio.run_coroutine_threadsafe(self.ws.close(), self._loop)
                except Exception:
                    pass
            else:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.ws.close())
                except RuntimeError:
                    pass
