"""Continuous Voice Activity Detection (VAD), Wake-Word Engine & Barge-In Listener."""

import re
import threading
import time
from typing import Any, Callable, Optional
import numpy as np

from voice.stt import FasterWhisperTranscriber

try:
    import sounddevice as sd
except ImportError:
    sd = None


def extract_wake_word_query(raw_text: str, trigger_word: str = "iris") -> Optional[str]:
    """Detects if raw_text contains the wake-word and extracts the clean following instruction."""
    if not raw_text:
        return None

    clean = raw_text.strip()
    # Matches "hey iris", "ok iris", "okay iris", "hi iris", "iris" at start or word boundary
    pattern = rf"\b(?:hey\s+|ok\s+|okay\s+|hi\s+)?{re.escape(trigger_word)}\b"
    match = re.search(pattern, clean, re.IGNORECASE)
    if not match:
        return None

    # Strip wake word
    query = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip()
    # Clean leading punctuation and double spaces
    query = re.sub(r"^[,\.:;\!\-\s]+", "", query).strip()
    query = re.sub(r"\s+", " ", query).strip()
    return query if query else "Hello Iris"


class ContinuousVoiceListener:
    """Non-blocking background voice activity listener with wake-word detection and barge-in interruption."""

    def __init__(
        self,
        transcriber: Optional[FasterWhisperTranscriber] = None,
        on_speech_detected: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[str, Optional[str]], None]] = None,
        samplerate: int = 16000,
        energy_threshold: float = 0.02,
        silence_duration: float = 0.8,
        require_wake_word: bool = True,
        trigger_word: str = "iris",
        tts_player: Optional[Any] = None,
    ):
        self.transcriber = transcriber or FasterWhisperTranscriber()
        self.on_speech_detected = on_speech_detected
        self.on_state_change = on_state_change
        self.samplerate = samplerate
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.require_wake_word = require_wake_word
        self.trigger_word = trigger_word
        self.tts_player = tts_player
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_listening = False

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def start(self) -> None:
        """Starts background continuous listening daemon thread."""
        if not sd or (self._thread is not None and self._thread.is_alive()):
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
        """Audio stream consumer detecting voice triggers and handling barge-in."""
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

                    # 1. Barge-In Interruption: Stop active TTS when user starts speaking
                    if self.tts_player and getattr(self.tts_player, "is_speaking", False):
                        if rms > self.energy_threshold * 1.8:
                            self.tts_player.stop()

                    # 2. Voice Activity Detection
                    if rms > self.energy_threshold:
                        if not is_speaking:
                            is_speaking = True
                            audio_buffer = []
                            if self.on_state_change:
                                try:
                                    self.on_state_change("listening", "Iris is listening...")
                                except Exception:
                                    pass
                        audio_buffer.append(audio_flat)
                        silence_start = time.time()
                    elif is_speaking:
                        audio_buffer.append(audio_flat)
                        if time.time() - silence_start > self.silence_duration:
                            # Speech ended -> Process & Transcribe
                            full_audio = np.concatenate(audio_buffer)
                            is_speaking = False
                            audio_buffer = []

                            if len(full_audio) > self.samplerate * 0.4:  # At least 0.4s of speech
                                if self.on_state_change:
                                    try:
                                        self.on_state_change("thinking", "Transcribing...")
                                    except Exception:
                                        pass
                                raw_text = self.transcriber.transcribe_audio_array(full_audio)
                                if raw_text:
                                    if self.require_wake_word:
                                        clean_query = extract_wake_word_query(raw_text, self.trigger_word)
                                        if clean_query:
                                            if self.on_state_change:
                                                try:
                                                    self.on_state_change("thinking", "Iris is thinking...")
                                                except Exception:
                                                    pass
                                            if self.on_speech_detected:
                                                try:
                                                    self.on_speech_detected(clean_query)
                                                except Exception as err:
                                                    print(f"[Continuous Listener Callback Error]: {err}")
                                        else:
                                            if self.on_state_change:
                                                try:
                                                    self.on_state_change("idle", None)
                                                except Exception:
                                                    pass
                                    else:
                                        if self.on_speech_detected:
                                            try:
                                                self.on_speech_detected(raw_text)
                                            except Exception as err:
                                                print(f"[Continuous Listener Callback Error]: {err}")
                                else:
                                    if self.on_state_change:
                                        try:
                                            self.on_state_change("idle", None)
                                        except Exception:
                                            pass

                    time.sleep(0.01)

        except Exception as e:
            print(f"[Continuous Listener Warning]: {e}")
        finally:
            self._is_listening = False
