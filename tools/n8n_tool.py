"""n8n Automation and Webhook Tool."""

from typing import Dict, Any, Optional
from integrations.n8n import N8nDispatcher
from tools.base import BaseTool, ToolResult


class TriggerN8nTool(BaseTool):
    """Tool for triggering external n8n automated workflows via webhooks."""

    name = "trigger_n8n_workflow"
    description = (
        "Triggers an external automation workflow on n8n (e.g. sending a Telegram message, "
        "updating a Notion database, sending emails, or triggering smart home webhooks)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "event_name": {
                "type": "string",
                "description": "Identifier name of the event or trigger (e.g. 'send_telegram', 'sync_task', 'notify_user').",
            },
            "payload": {
                "type": "object",
                "description": "JSON dictionary payload containing variables or data to send to the workflow.",
            },
            "custom_webhook_url": {
                "type": "string",
                "description": "Optional specific webhook URL to override the default N8N_WEBHOOK_URL.",
            },
        },
        "required": ["event_name"],
    }

    def __init__(self):
        self.dispatcher = N8nDispatcher()

    def execute(
        self,
        event_name: str,
        payload: Optional[Dict[str, Any]] = None,
        custom_webhook_url: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        success, message = self.dispatcher.trigger(
            event_name=event_name,
            payload=payload or {},
            custom_url=custom_webhook_url,
        )
        return ToolResult(
            success=success,
            output=message if success else "",
            error=None if success else message,
        )
