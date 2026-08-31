"""Configuration loader using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Miko API Configuration
    api_key: str = Field(default="", validation_alias="MIKO_API_KEY")
    base_url: str = Field(
        default="https://api-miko.yokoya.space",
        validation_alias="MIKO_BASE_URL"
    )
    service: str = Field(
        default="qwen-max",
        validation_alias="MIKO_SERVICE"
    )
    username: str = Field(
        default="iris_user",
        validation_alias="MIKO_USERNAME"
    )
    userid: str = Field(
        default="iris_local_1",
        validation_alias="MIKO_USERID"
    )

    # Model Features (Search enabled by default for real-time web awareness)
    search: bool = Field(default=True, validation_alias="MIKO_SEARCH")
    thinking: bool = Field(default=False, validation_alias="MIKO_THINKING")

    # Behavior
    system_prompt: str = Field(
        default="You are Iris, an intelligent desktop AI assistant.",
        validation_alias="SYSTEM_PROMPT"
    )
    max_history_messages: int = Field(
        default=20,
        validation_alias="MAX_HISTORY_MESSAGES"
    )
    timeout_seconds: float = Field(default=60.0, validation_alias="REQUEST_TIMEOUT_SECONDS")

    # Optional n8n Webhook
    n8n_webhook_url: str = Field(default="", validation_alias="N8N_WEBHOOK_URL")


# Global singleton instance
config = AppConfig()
