"""Iris Desktop UI Subsystem (Floating HUD, Wavy Voice Overlay, and Response Splitter)."""

from ui.chat_window import FloatingChatWindow
from ui.overlay import VoiceListeningOverlay
from ui.hotkey import GlobalUIHotkeyListener
from ui.formatter import clean_markdown_for_speech, extract_concise_spoken_summary
from ui.app import IrisUIApp

__all__ = [
    "FloatingChatWindow",
    "VoiceListeningOverlay",
    "GlobalUIHotkeyListener",
    "clean_markdown_for_speech",
    "extract_concise_spoken_summary",
    "IrisUIApp",
]
