"""High-performance Microsoft Edge Neural Text-To-Speech streaming engine."""

import asyncio
import io
import threading
from typing import Optional
from config import config

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    import sounddevice as sd
    import soundfile as sf
except ImportError:
    sd = None
    sf = None


class EdgeTTSPlayer:
    """Zero-cost streaming TTS using Microsoft Edge Neural Voices."""

    def __init__(
        self,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: str = "+0Hz",
    ):
        self.voice = voice or config.voice_tts_voice
        self.rate = rate or config.voice_tts_rate
        self.pitch = pitch
        self._is_speaking = False
        self._stop_event = threading.Event()

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    async def _synthesize_to_bytes(self, text: str) -> bytes:
        """Asynchronously streams audio bytes from edge-tts."""
        if not edge_tts:
            raise RuntimeError("edge-tts library is not installed.")

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
        )
        audio_stream = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])
        return audio_stream.getvalue()

    def speak(self, text: str, block: bool = True) -> bool:
        """Synthesizes text and plays audio through default speaker endpoint."""
        clean_text = text.strip()
        if not clean_text:
            return False

        if not edge_tts or not sd or not sf:
            print("[Voice Warning] Audio playback libraries (edge-tts, sounddevice, soundfile) not available.")
            return False

        self._stop_event.clear()
        self._is_speaking = True

        try:
            # Run async synthesis in a clean event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If called inside an active loop, use a new thread or nest
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        audio_bytes = executor.submit(asyncio.run, self._synthesize_to_bytes(clean_text)).result()
                else:
                    audio_bytes = loop.run_until_complete(self._synthesize_to_bytes(clean_text))
            except RuntimeError:
                audio_bytes = asyncio.run(self._synthesize_to_bytes(clean_text))

            if not audio_bytes or self._stop_event.is_set():
                return False

            # Decode MP3 into float32 PCM in memory
            with sf.SoundFile(io.BytesIO(audio_bytes)) as sound_file:
                data = sound_file.read(dtype="float32")
                samplerate = sound_file.samplerate

                sd.play(data, samplerate=samplerate)
                if block:
                    sd.wait()
            return True

        except Exception as e:
            print(f"[EdgeTTS Error]: {e}")
            return False
        finally:
            self._is_speaking = False

    def speak_async(self, text: str) -> threading.Thread:
        """Dispatches speech playback to a background daemon thread."""
        thread = threading.Thread(target=self.speak, args=(text, True), daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        """Instantly terminates any active audio synthesis or playback."""
        self._stop_event.set()
        if sd:
            try:
                sd.stop()
            except Exception:
                pass
        self._is_speaking = False
