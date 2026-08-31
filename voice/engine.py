"""High-level Voice Subsystem Coordinator for Iris."""

from typing import Callable, Optional
from voice.tts import EdgeTTSPlayer
from voice.stt import FasterWhisperTranscriber
from voice.listener import ContinuousVoiceListener


class VoiceEngine:
    """Coordinates neural speech synthesis, speech recognition, and wake-word loop."""

    def __init__(self):
        self.tts = EdgeTTSPlayer()
        self.stt = FasterWhisperTranscriber()
        self._listener: Optional[ContinuousVoiceListener] = None

    @property
    def is_listening_loop(self) -> bool:
        return self._listener is not None and self._listener.is_listening

    def speak(self, text: str, block: bool = True) -> bool:
        """Speaks text using edge-tts."""
        return self.tts.speak(text, block=block)

    def speak_async(self, text: str):
        """Speaks text in non-blocking background thread."""
        return self.tts.speak_async(text)

    def listen(self, duration_seconds: float = 5.0) -> str:
        """Listens from microphone and returns transcribed text."""
        return self.stt.listen_and_transcribe(duration_seconds=duration_seconds)

    def start_wake_word_loop(
        self,
        on_command_callback: Callable[[str], None],
        on_state_change: Optional[Callable[[str, Optional[str]], None]] = None,
        trigger_word: str = "iris",
    ) -> bool:
        """Starts continuous wake-word listening with barge-in interruption in the background."""
        if self._listener and self._listener.is_listening:
            return True

        self._listener = ContinuousVoiceListener(
            transcriber=self.stt,
            on_speech_detected=on_command_callback,
            on_state_change=on_state_change,
            require_wake_word=True,
            trigger_word=trigger_word,
            tts_player=self.tts,
        )
        self._listener.start()
        return True

    def stop_wake_word_loop(self) -> None:
        """Stops background continuous wake-word listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None

    def stop(self) -> None:
        """Stops active speech output and wake-word listener."""
        self.tts.stop()
        self.stop_wake_word_loop()
