"""Configuration loader using Pydantic Settings and JSON prompt templates."""

import json
from pathlib import Path
from pydantic import Field, AliasChoices
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

    # Prompt configuration file
    prompt_file: str = Field(default="prompts.json", validation_alias="PROMPT_FILE")

    # Runtime Settings
    max_history_messages: int = Field(
        default=20,
        validation_alias="MAX_HISTORY_MESSAGES"
    )
    timeout_seconds: float = Field(default=60.0, validation_alias="REQUEST_TIMEOUT_SECONDS")
    memory_db_path: str = Field(default=".iris_memory.db", validation_alias="IRIS_MEMORY_DB_PATH")
    max_requests_per_second: float = Field(default=2.0, validation_alias="IRIS_MAX_REQUESTS_PER_SECOND")
    max_inline_system_prompt_chars: int = Field(default=32000, validation_alias="IRIS_MAX_INLINE_SYSTEM_PROMPT_CHARS")
    max_inline_user_chars: int = Field(default=16000, validation_alias="IRIS_MAX_INLINE_USER_CHARS")

    # Optional n8n Webhook
    n8n_webhook_url: str = Field(default="", validation_alias="N8N_WEBHOOK_URL")

    # Discord Userbot Bridge Configuration
    discord_user_token: str = Field(
        default="",
        validation_alias=AliasChoices("DISCORD_USER_TOKEN", "USER_TOKEN", "ERIXA_USER_TOKEN")
    )
    discord_trigger_word: str = Field(default="iris", validation_alias="DISCORD_TRIGGER_WORD")
    discord_allowed_users: str = Field(default="", validation_alias="DISCORD_ALLOWED_USERS")
    discord_autostart: bool = Field(default=False, validation_alias="DISCORD_AUTOSTART")

    # Vision Engine Configuration
    vision_service: str = Field(
        default="qwen-max",
        validation_alias="MIKO_VISION_SERVICE"
    )
    vision_cache_dir: str = Field(
        default=".iris_cache",
        validation_alias="IRIS_VISION_CACHE_DIR"
    )
    vision_compress_quality: int = Field(
        default=85,
        validation_alias="IRIS_VISION_COMPRESS_QUALITY"
    )
    vision_max_dimension: int = Field(
        default=1920,
        validation_alias="IRIS_VISION_MAX_DIMENSION"
    )
    vision_grid_overlay: bool = Field(
        default=False,
        validation_alias="IRIS_VISION_GRID_OVERLAY"
    )

    # Desktop Actuator Configuration
    actuator_enabled: bool = Field(
        default=True,
        validation_alias="IRIS_ACTUATOR_ENABLED"
    )
    actuator_typing_delay: float = Field(
        default=0.02,
        validation_alias="IRIS_ACTUATOR_TYPING_DELAY"
    )
    actuator_mouse_duration: float = Field(
        default=0.2,
        validation_alias="IRIS_ACTUATOR_MOUSE_DURATION"
    )

    # Global Panic Killswitch
    killswitch_hotkey: str = Field(
        default="<ctrl>+<shift>+k",
        validation_alias="IRIS_KILLSWITCH_HOTKEY"
    )

    # Voice Engine Configuration
    voice_enabled: bool = Field(
        default=False,
        validation_alias="IRIS_VOICE_ENABLED"
    )
    voice_tts_voice: str = Field(
        default="en-US-AvaMultilingualNeural",
        validation_alias="IRIS_VOICE_TTS_VOICE"
    )
    voice_tts_rate: str = Field(
        default="+0%",
        validation_alias="IRIS_VOICE_TTS_RATE"
    )
    voice_stt_model: str = Field(
        default="base.en",
        validation_alias="IRIS_VOICE_STT_MODEL"
    )
    voice_stt_compute: str = Field(
        default="int8",
        validation_alias="IRIS_VOICE_STT_COMPUTE"
    )
    voice_concise_mode: bool = Field(
        default=True,
        validation_alias="IRIS_VOICE_CONCISE_MODE"
    )

    # Desktop HUD & UI Overlay Configuration
    ui_enabled: bool = Field(
        default=True,
        validation_alias="IRIS_UI_ENABLED"
    )
    ui_hotkey: str = Field(
        default="<ctrl>+<shift>+t",
        validation_alias="IRIS_UI_HOTKEY"
    )
    ui_width: int = Field(
        default=390,
        validation_alias="IRIS_UI_WIDTH"
    )
    ui_height: int = Field(
        default=540,
        validation_alias="IRIS_UI_HEIGHT"
    )
    ui_top_margin: int = Field(
        default=36,
        validation_alias="IRIS_UI_TOP_MARGIN"
    )
    ui_right_margin: int = Field(
        default=28,
        validation_alias="IRIS_UI_RIGHT_MARGIN"
    )
    ui_theme_accent: str = Field(
        default="#38bdf8",
        validation_alias="IRIS_UI_THEME_ACCENT"
    )

    def get_prompt(self, key: str, default: str = "") -> str:
        """Loads a specific prompt template by key from prompts.json."""
        prompt_path = Path(self.prompt_file)
        if prompt_path.exists():
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and key in data:
                        return data[key]
            except Exception:
                pass
        return default

    @property
    def system_prompt(self) -> str:
        return self.get_prompt("system_prompt", "You are Iris, a smart and helpful local desktop AI assistant.")

    @property
    def goal_prompt(self) -> str:
        return self.get_prompt("goal_prompt", "You are Iris operating in Autonomous ReAct Goal Mode.")

    @property
    def actuator_prompt(self) -> str:
        return self.get_prompt("actuator_prompt", "You are Iris operating in Single Desktop Actuator Mode.")

    @property
    def vision_prompt(self) -> str:
        return self.get_prompt("vision_prompt", "You are Iris operating in Screen Vision & UI Inspection Mode.")

    @property
    def router_prompt(self) -> str:
        return self.get_prompt("router_prompt", "You are the Iris Fast Intent Classifier.")

    @property
    def memory_prompt(self) -> str:
        return self.get_prompt("memory_prompt", "You are the Iris Memory Extraction Engine.")


# Global singleton instance
config = AppConfig()
