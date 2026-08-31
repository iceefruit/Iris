"""Continuous Voice Activity Detection (VAD), Wake-Word Engine & Barge-In Listener."""

import re
import threading
import time
from typing import Any, Callable, Optional
import numpy as np

from config import config
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
    # Flexible pattern for wake words: "hey iris", "ok iris", "hi iris", "hello iris", "iris", "iris,"
    # Also matches common phonetic Whisper mishearings: iris, irish, aires, airis
    pattern = rf"(?i)\b(?:hey|ok|okay|hi|hello|yo)?[\s,:-]*(?:{re.escape(trigger_word)}|irish|aires|airis)\b[\s,:\.\?!-]*"
    match = re.search(pattern, clean)
    if not match:
        return None

    # Strip wake word match
    query = clean[match.end():].strip()
    # Clean leading and trailing punctuation
    query = re.sub(r"^[,\.:;\!\-\s]+", "", query).strip()
    query = re.sub(r"\s+", " ", query).strip()
    return query if query else "Hello Iris"


def is_acoustic_echo(candidate: str, last_spoken: str) -> bool:
    """Detects if transcribed candidate text is an acoustic feedback echo of Iris's recent speech."""
    if not candidate or not last_spoken:
        return False

    def normalize(s: str) -> str:
        return re.sub(r"[^\w\s]", "", s.lower()).strip()

    c_norm = normalize(candidate)
    s_norm = normalize(last_spoken)

    if not c_norm or not s_norm:
        return False

    # Exact or substring match
    if c_norm == s_norm or c_norm in s_norm or (len(c_norm) > 10 and s_norm in c_norm):
        return True

    # Word overlap match (>70% words match recent assistant output)
    c_words = set(c_norm.split())
    s_words = set(s_norm.split())
    if not c_words:
        return False

    overlap = len(c_words.intersection(s_words)) / len(c_words)
    return overlap >= 0.70


class ContinuousVoiceListener:
    """Non-blocking background voice activity listener with wake-word detection, multi-turn follow-up, and AEC."""

    def __init__(
        self,
        transcriber: Optional[FasterWhisperTranscriber] = None,
        on_speech_detected: Optional[Callable[[str], None]] = None,
        on_state_change: Optional[Callable[[str, Optional[str]], None]] = None,
        samplerate: int = 16000,
        energy_threshold: Optional[float] = None,
        silence_duration: float = 0.8,
        require_wake_word: bool = True,
        trigger_word: str = "iris",
        tts_player: Optional[Any] = None,
    ):
        self.transcriber = transcriber or FasterWhisperTranscriber()
        self.on_speech_detected = on_speech_detected
        self.on_state_change = on_state_change
        self.samplerate = samplerate
        self.energy_threshold = energy_threshold if energy_threshold is not None else getattr(config, "voice_energy_threshold", 0.008)
        self.silence_duration = silence_duration
        self.require_wake_word = require_wake_word
        self.trigger_word = trigger_word
        self.tts_player = tts_player
        self.last_spoken_text: str = ""
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_listening = False
        self._follow_up_expiry = 0.0
        self._in_follow_up_state = False
        self._tts_last_active_time = 0.0

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def set_last_spoken_text(self, text: str) -> None:
        """Stores the recent assistant speech to filter out acoustic echoes."""
        self.last_spoken_text = text or ""

    def activate_follow_up(self, duration_seconds: float = 7.0) -> None:
        """Enables multi-turn conversational follow-up mode without repeating the wake word."""
        self._follow_up_expiry = time.time() + duration_seconds
        self._in_follow_up_state = True
        if self.on_state_change:
            try:
                self.on_state_change("listening", "Listening for follow-up...")
            except Exception:
                pass

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
        self._follow_up_expiry = 0.0
        self._in_follow_up_state = False

    def _listener_loop(self) -> None:
        """Audio stream consumer with infinite auto-reconnect and wake-word/follow-up detection."""
        block_size = int(self.samplerate * 0.1)  # 100ms blocks
        audio_buffer = []
        is_speaking = False
        silence_start = 0.0

        while not self._stop_event.is_set():
            try:
                with sd.InputStream(
                    samplerate=self.samplerate,
                    channels=1,
                    dtype="float32",
                    blocksize=block_size,
                ) as stream:
                    while not self._stop_event.is_set():
                        now = time.time()

                        # Check follow-up expiration
                        if self._in_follow_up_state and now > self._follow_up_expiry:
                            self._in_follow_up_state = False
                            self._follow_up_expiry = 0.0
                            if self.on_state_change and not is_speaking:
                                try:
                                    self.on_state_change("idle", None)
                                except Exception:
                                    pass

                        data, _ = stream.read(block_size)
                        audio_flat = data.flatten()
                        rms = np.sqrt(np.mean(audio_flat**2))

                        # 1. Hardware Echo Suppression: Mute mic recording while Iris is speaking out loud
                        is_tts_active = bool(self.tts_player and getattr(self.tts_player, "is_speaking", False))
                        if is_tts_active:
                            self._tts_last_active_time = now
                            audio_buffer = []
                            is_speaking = False
                            time.sleep(0.02)
                            continue

                        # Post-TTS speaker reverberation cooldown (0.5s grace period)
                        if now - self._tts_last_active_time < 0.5:
                            audio_buffer = []
                            is_speaking = False
                            time.sleep(0.02)
                            continue

                        # 2. Voice Activity Detection
                        if rms > self.energy_threshold:
                            if not is_speaking:
                                is_speaking = True
                                audio_buffer = []
                                if self.on_state_change:
                                    try:
                                        prompt_label = "Listening for follow-up..." if self._in_follow_up_state else "Iris is listening..."
                                        self.on_state_change("listening", prompt_label)
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
                                    if raw_text and raw_text.strip():
                                        # 3. Acoustic Echo Cancellation (only active within 2.0s of TTS completion)
                                        if (now - self._tts_last_active_time < 2.0) and is_acoustic_echo(raw_text, self.last_spoken_text):
                                            audio_buffer = []
                                            is_speaking = False
                                            continue

                                        in_follow_up = self._in_follow_up_state or (time.time() < self._follow_up_expiry)

                                        if self.require_wake_word and not in_follow_up:
                                            clean_query = extract_wake_word_query(raw_text, self.trigger_word)
                                            if clean_query:
                                                self._in_follow_up_state = False
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
                                            # Active conversational mode or follow-up turn
                                            clean_query = extract_wake_word_query(raw_text, self.trigger_word) or raw_text.strip()
                                            clean_lower = clean_query.lower()

                                            # Stop phrases to exit conversation gracefully
                                            if clean_lower in ("stop", "bye", "goodbye", "nevermind", "cancel", "exit", "quiet", "thanks", "thank you"):
                                                self._in_follow_up_state = False
                                                self._follow_up_expiry = 0.0
                                                if self.on_state_change:
                                                    try:
                                                        self.on_state_change("idle", None)
                                                    except Exception:
                                                        pass
                                            elif clean_query and self.on_speech_detected:
                                                self._in_follow_up_state = False
                                                if self.on_state_change:
                                                    try:
                                                        self.on_state_change("thinking", "Iris is thinking...")
                                                    except Exception:
                                                        pass
                                                try:
                                                    self.on_speech_detected(clean_query)
                                                except Exception as err:
                                                    print(f"[Continuous Listener Callback Error]: {err}")
                                    else:
                                        if self.on_state_change and not self._in_follow_up_state:
                                            try:
                                                self.on_state_change("idle", None)
                                            except Exception:
                                                pass

                        time.sleep(0.01)

            except Exception as e:
                if not self._stop_event.is_set():
                    print(f"[Continuous Listener Warning]: Audio stream error: {e}. Reconnecting...")
                    time.sleep(0.5)

        self._is_listening = False
