"""High-level Voice Subsystem Coordinator for Iris."""

from typing import Optional
from voice.tts import EdgeTTSPlayer
from voice.stt import FasterWhisperTranscriber


class VoiceEngine:
    """Coordinates neural speech synthesis and local speech recognition."""

    def __init__(self):
        self.tts = EdgeTTSPlayer()
        self.stt = FasterWhisperTranscriber()

    def speak(self, text: str, block: bool = True) -> bool:
        """Speaks text using edge-tts."""
        return self.tts.speak(text, block=block)

    def speak_async(self, text: str):
        """Speaks text in non-blocking background thread."""
        return self.tts.speak_async(text)

    def listen(self, duration_seconds: float = 5.0) -> str:
        """Listens from microphone and returns transcribed text."""
        return self.stt.listen_and_transcribe(duration_seconds=duration_seconds)

    def stop(self) -> None:
        """Stops active speech output."""
        self.tts.stop()
