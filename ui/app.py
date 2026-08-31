"""Central PySide6 GUI Application and Coordinator for Iris."""

import os
import sys
import threading
from typing import Optional

# Ensure high-DPI scaling before Qt initializes
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from config import config
from core.agent import IrisAgent
from core.client import MikoClient
from core.memory_store import PersistentMemoryStore
from core.killswitch import killswitch
from vision import VisionEngine
from voice import VoiceEngine
from ui.chat_window import FloatingChatWindow
from ui.overlay import VoiceListeningOverlay
from ui.hotkey import GlobalUIHotkeyListener
from ui.formatter import extract_concise_spoken_summary


class AgentWorkerSignals(QObject):
    user_message_received = Signal(str)
    assistant_started = Signal()
    chunk_received = Signal(str)
    response_completed = Signal(str, bool)  # full_response, is_voice
    error_occurred = Signal(str)
    state_changed = Signal(str, str)  # state, text


class IrisUIApp:
    """Master controller managing the Qt Event Loop, Floating Chat HUD, and Voice Overlay."""

    def __init__(
        self,
        agent: Optional[IrisAgent] = None,
        voice_engine: Optional[VoiceEngine] = None,
        vision_engine: Optional[VisionEngine] = None,
    ):
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
            self.app.setApplicationName("Iris AI Assistant")
            self.app.setQuitOnLastWindowClosed(False)

        # Core systems
        if agent is None:
            client = MikoClient(
                base_url=config.base_url,
                api_key=config.api_key,
                default_service=config.service,
                username=config.username,
                userid=config.userid,
                timeout=config.timeout_seconds,
            )
            memory = PersistentMemoryStore(db_path=config.memory_db_path)
            self.agent = IrisAgent(client=client, memory=memory, killswitch=killswitch)
        else:
            self.agent = agent

        # Clear old server-side and local conversation session on fresh startup
        try:
            self.agent.clear()
        except Exception:
            pass

        self.voice = voice_engine or VoiceEngine()
        self.vision = vision_engine or VisionEngine()

        # GUI Components
        self.chat_window = FloatingChatWindow()
        self.overlay = VoiceListeningOverlay()
        self.hotkey_listener = GlobalUIHotkeyListener(config.ui_hotkey)

        # Worker signals for cross-thread GUI safety
        self.signals = AgentWorkerSignals()
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Binds Qt signals strictly to the main GUI thread."""
        # 1. Hotkey toggle (Ctrl+Shift+T)
        self.hotkey_listener.signals.toggle_hud.connect(self.chat_window.toggle_visibility)

        # 2. Chat window user input
        self.chat_window.message_submitted.connect(self._handle_user_message)
        self.chat_window.voice_toggled.connect(self._handle_mic_button_clicked)

        # 3. Thread-safe Agent signals -> UI updates
        self.signals.user_message_received.connect(self.chat_window.add_user_message)
        self.signals.assistant_started.connect(self.chat_window.start_assistant_message)
        self.signals.chunk_received.connect(self.chat_window.append_assistant_chunk)
        self.signals.response_completed.connect(self._on_response_completed)
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.error_occurred.connect(self._on_error_occurred)

    def start(self, show_chat: bool = True, start_wake_word: bool = True) -> int:
        """Starts all UI elements and enters the Qt event loop."""
        killswitch.start()

        # Start global hotkey listener
        self.hotkey_listener.start()

        if show_chat:
            self.chat_window.show()

        if start_wake_word:
            self._start_voice_wake_word_loop()

        return self.app.exec()

    def _start_voice_wake_word_loop(self) -> None:
        """Starts continuous wake-word listener connected to visual overlay."""
        def on_wake_speech(query: str):
            self.signals.state_changed.emit("thinking", f"Iris: {query}")
            threading.Thread(target=self._process_voice_query, args=(query,), daemon=True).start()

        def on_voice_state(state: str, text: Optional[str]):
            self.signals.state_changed.emit(state, text or f"Iris is {state}...")

        self.voice.start_wake_word_loop(
            on_command_callback=on_wake_speech,
            on_state_change=on_voice_state,
        )

    def _handle_mic_button_clicked(self) -> None:
        """Handles manual microphone trigger from the chat window."""
        if not self.voice.is_listening_loop:
            self._start_voice_wake_word_loop()
        self.voice.activate_follow_up(duration_seconds=8.0)
        self.signals.state_changed.emit("listening", "Listening for speech...")

    def _handle_user_message(self, text: str) -> None:
        """Processes message submitted through the Chat HUD input."""
        threading.Thread(
            target=self._process_text_query,
            args=(text, False),
            daemon=True
        ).start()

    def _process_voice_query(self, query: str) -> None:
        """Processes voice command: shows in chat window, runs agent, speaks concise summary."""
        self.signals.user_message_received.emit(query)
        self._process_text_query(query, is_voice_reply=True)

    def _process_text_query(self, user_input: str, is_voice_reply: bool = False) -> None:
        """Streams agent response and triggers spoken output if required."""
        self.signals.state_changed.emit("thinking", "Iris is thinking...")
        self.signals.assistant_started.emit()

        try:
            full_response = ""
            lower = user_input.strip().lower()

            if lower.startswith("/act ") or lower.startswith("/goal "):
                goal_text = user_input.strip()[5:].strip() if lower.startswith("/act ") else user_input.strip()[6:].strip()
                result = self.agent.run_goal(goal_text)
                full_response = result.final_answer or "Action complete."
                self.signals.chunk_received.emit(full_response)
            else:
                speak_explicit = lower.startswith("/speak ")
                clean_input = user_input[7:].strip() if speak_explicit else user_input
                if speak_explicit:
                    is_voice_reply = True

                for chunk in self.agent.ask(clean_input, execute_actions=True):
                    if chunk.chunk_type == "content" and chunk.text:
                        full_response += chunk.text
                        self.signals.chunk_received.emit(chunk.text)
                    elif chunk.chunk_type == "function_call":
                        action_msg = f"\n⚡ *{chunk.text}*...\n"
                        self.signals.chunk_received.emit(action_msg)
                    elif chunk.chunk_type == "function_result":
                        res_msg = f"✔ *{chunk.text}*\n"
                        self.signals.chunk_received.emit(res_msg)
                    elif chunk.chunk_type == "error":
                        full_response += f"\n{chunk.text}"
                        self.signals.chunk_received.emit(chunk.text)

            self.signals.response_completed.emit(full_response, is_voice_reply)

        except Exception as e:
            self.signals.error_occurred.emit(str(e))

    def _on_state_changed(self, state: str, text: str) -> None:
        """Updates both overlay pill and chat window status."""
        self.overlay.set_listening_state(state, text)
        self.chat_window.set_status(text or state, state)

    def _on_response_completed(self, full_text: str, is_voice: bool) -> None:
        """Finalizes chat message and speaks concise summary with conversational follow-up."""
        self.chat_window.finish_assistant_message(full_text)

        if is_voice:
            spoken_summary = extract_concise_spoken_summary(full_text)
            if spoken_summary:
                self.signals.state_changed.emit("speaking", "Iris is speaking...")

                def _speak_thread():
                    try:
                        self.voice.speak(spoken_summary, block=True)
                    except Exception as err:
                        print(f"[Voice Playback Error]: {err}")
                    finally:
                        # Multi-turn conversation: remain open for follow-up turns without wake-word
                        self.voice.activate_follow_up(duration_seconds=7.0)
                        self.signals.state_changed.emit("listening", "Listening for follow-up...")

                threading.Thread(target=_speak_thread, daemon=True).start()
            else:
                self.voice.activate_follow_up(duration_seconds=7.0)
                self.signals.state_changed.emit("listening", "Listening for follow-up...")
        else:
            self.signals.state_changed.emit("idle", "")

    def _on_error_occurred(self, error_msg: str) -> None:
        self.chat_window.finish_assistant_message(f"⚠️ **Error:** {error_msg}")
        self.signals.state_changed.emit("idle", "")

    def stop(self) -> None:
        """Shuts down UI and listeners gracefully."""
        self.hotkey_listener.stop()
        self.voice.stop()
        self.chat_window.close()
        self.overlay.close()
