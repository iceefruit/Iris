"""Configuration loader using Pydantic Settings."""

import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Configuration
    api_key: str = Field(default="", validation_alias="MIKO_API_KEY")
    base_url: str = Field(
        default="https://api-miko.yokoya.space/v1",
        validation_alias="MIKO_BASE_URL"
    )
    model: str = Field(
        default="gemini-2.5-flash",
        validation_alias="MIKO_MODEL"
    )

    # Behavior
    system_prompt: str = Field(
        default="You are Iris, an intelligent desktop AI assistant.",
        validation_alias="SYSTEM_PROMPT"
    )
    max_history_messages: int = Field(
        default=20,
        validation_alias="MAX_HISTORY_MESSAGES"
    )
    temperature: float = Field(default=0.7, validation_alias="TEMPERATURE")
    timeout_seconds: float = Field(default=60.0, validation_alias="REQUEST_TIMEOUT_SECONDS")

    # Optional n8n Webhook
    n8n_webhook_url: str = Field(default="", validation_alias="N8N_WEBHOOK_URL")


# Global singleton instance
config = AppConfig()
