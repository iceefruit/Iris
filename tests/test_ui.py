"""Unit tests for Iris Desktop UI, Floating Chat HUD, and Wavy Voice Overlay."""

import pytest
from PySide6.QtWidgets import QApplication
from ui.formatter import clean_markdown_for_speech, extract_concise_spoken_summary
from ui.chat_window import FloatingChatWindow, format_markdown_to_rich_html
from ui.overlay import VoiceListeningOverlay
from ui.hotkey import GlobalUIHotkeyListener


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_formatter_cleans_markdown_and_charts():
    raw_text = """
Here is the CPU utilization:
```bash
cpu: 45%
mem: 60%
```
┌─────────────────┐
│ System: Active  │
│ Load:   45% [█] │
└─────────────────┘

• Point 1: Everything is running smoothly.
• Point 2: Battery is at 95%.

Visit https://example.com for more info!
"""
    cleaned = clean_markdown_for_speech(raw_text)
    # Ensure code blocks, URLs, and ASCII boxes are cleaned for speech
    assert "┌" not in cleaned
    assert "cpu:" not in cleaned
    assert "https://" not in cleaned
    assert "Everything is running smoothly" in cleaned

    spoken_summary = extract_concise_spoken_summary(raw_text)
    assert len(spoken_summary) > 0
    assert "Here is the CPU utilization" in spoken_summary or "Everything is running smoothly" in spoken_summary


def test_format_markdown_to_rich_html():
    raw_text = "**Hello** and *welcome*!\n```python\nprint('test')\n```"
    rich_html = format_markdown_to_rich_html(raw_text)
    assert "<strong" in rich_html
    assert "Consolas" in rich_html
    assert "print(&#x27;test&#x27;)" in rich_html or "print('test')" in rich_html


def test_chat_window_initialization(qapp):
    chat = FloatingChatWindow()
    assert chat.width() > 0
    assert chat.height() > 0
    assert chat.title_label.text() == "✨ Iris HUD"

    # Test adding messages
    chat.add_user_message("Hello from user!")
    chat.start_assistant_message()
    chat.append_assistant_chunk("Hello! ")
    chat.append_assistant_chunk("How can I help you today?")
    chat.finish_assistant_message()

    # Test toggling
    chat.toggle_visibility()
    assert chat.isVisible()
    chat.toggle_visibility()
    assert not chat.isVisible()


def test_overlay_initialization_and_states(qapp):
    overlay = VoiceListeningOverlay()
    assert overlay.current_state == "idle"

    # Test state transitions
    overlay.set_listening_state("listening", "Iris is listening...")
    assert overlay.is_active is True
    assert overlay.status_text == "Iris is listening..."

    overlay.set_listening_state("thinking", "Iris is thinking...")
    assert overlay.current_state == "thinking"

    overlay.set_listening_state("speaking", "Iris is speaking...")
    assert overlay.current_state == "speaking"

    overlay.set_listening_state("idle")
    assert overlay.is_active is False

    # Simulate animation frame
    overlay._on_animation_frame()
    assert overlay.phase > 0.0


def test_hotkey_listener_initialization():
    listener = GlobalUIHotkeyListener("<ctrl>+<shift>+t")
    assert listener.hotkey_str == "<ctrl>+<shift>+t"
    assert listener.signals is not None
