"""Continuous Voice Activity Detection (VAD) and Background Listener."""

import threading
import time
from typing import Callable, Optional
import numpy as np

from voice.stt import FasterWhisperTranscriber

try:
    import sounddevice as sd
except ImportError:
    sd = None


class ContinuousVoiceListener:
    """Non-blocking background voice activity listener with automatic transcription."""

    def __init__(
        self,
        transcriber: Optional[FasterWhisperTranscriber] = None,
        on_speech_detected: Optional[Callable[[str], None]] = None,
        samplerate: int = 16000,
        energy_threshold: float = 0.02,
        silence_duration: float = 0.8,
    ):
        self.transcriber = transcriber or FasterWhisperTranscriber()
        self.on_speech_detected = on_speech_detected
        self.samplerate = samplerate
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_listening = False

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def start(self) -> None:
        """Starts background continuous listening daemon thread."""
        if not sd or self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listener_loop, daemon=True)
        self._thread.start()
        self._is_listening = True

    def stop(self) -> None:
        """Stops background listening."""
        self._stop_event.set()
        self._is_listening = False

    def _listener_loop(self) -> None:
        """Audio stream consumer detecting voice triggers."""
        block_size = int(self.samplerate * 0.1)  # 100ms blocks
        audio_buffer = []
        is_speaking = False
        silence_start = 0.0

        try:
            with sd.InputStream(
                samplerate=self.samplerate,
                channels=1,
                dtype="float32",
                blocksize=block_size,
            ) as stream:
                while not self._stop_event.is_set():
                    data, _ = stream.read(block_size)
                    audio_flat = data.flatten()
                    rms = np.sqrt(np.mean(audio_flat**2))

                    if rms > self.energy_threshold:
                        if not is_speaking:
                            is_speaking = True
                            audio_buffer = []
                        audio_buffer.append(audio_flat)
                        silence_start = time.time()
                    elif is_speaking:
                        audio_buffer.append(audio_flat)
                        if time.time() - silence_start > self.silence_duration:
                            # Speech ended -> Transcribe
                            full_audio = np.concatenate(audio_buffer)
                            is_speaking = False
                            audio_buffer = []

                            if len(full_audio) > self.samplerate * 0.5:  # At least 0.5s of audio
                                text = self.transcriber.transcribe_audio_array(full_audio)
                                if text and self.on_speech_detected:
                                    try:
                                        self.on_speech_detected(text)
                                    except Exception as err:
                                        print(f"[Continuous Listener Callback Error]: {err}")

                    time.sleep(0.01)

        except Exception as e:
            print(f"[Continuous Listener Warning]: {e}")
        finally:
            self._is_listening = False
