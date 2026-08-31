"""Asynchronous/synchronous webhook dispatcher for n8n workflows."""

from typing import Any, Dict, Optional, Tuple
import httpx
from config import config


class N8nDispatcher:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or config.n8n_webhook_url

    def trigger(
        self, event_name: str, payload: Dict[str, Any], custom_url: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Sends an event payload to a configured n8n webhook."""
        url = custom_url or self.webhook_url
        if not url:
            return False, "No n8n Webhook URL configured. Please set N8N_WEBHOOK_URL in .env."

        data = {
            "event": event_name,
            "data": payload,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=data)
                if res.status_code in (200, 201, 204):
                    return True, f"n8n webhook triggered successfully [{res.status_code}]: {res.text[:200]}"
                else:
                    return False, f"n8n webhook returned status {res.status_code}: {res.text[:200]}"
        except Exception as e:
            return False, f"Failed to reach n8n webhook: {str(e)}"
