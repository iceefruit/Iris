"""Asynchronous/synchronous webhook dispatcher for n8n workflows."""

import httpx
from typing import Dict, Any, Optional


class N8nDispatcher:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    def trigger(self, event_name: str, payload: Dict[str, Any]) -> bool:
        """Sends an event payload to a configured n8n webhook."""
        if not self.webhook_url:
            return False

        data = {
            "event": event_name,
            "data": payload
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(self.webhook_url, json=data)
                return res.status_code in (200, 201, 204)
        except Exception:
            return False
