"""Low-latency local Speech-To-Text transcriber using faster-whisper."""

import io
from typing import Optional, Any
import numpy as np
from config import config

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


class FasterWhisperTranscriber:
    """Efficient local speech recognizer with lazy loading."""

    def __init__(
        self,
        model_size: Optional[str] = None,
        compute_type: Optional[str] = None,
        samplerate: int = 16000,
    ):
        self.model_size = model_size or config.voice_stt_model
        self.compute_type = compute_type or config.voice_stt_compute
        self.samplerate = samplerate
        self._model: Optional[Any] = None

    @property
    def model(self):
        """Lazy loader for Whisper model to save memory until first use."""
        if self._model is None:
            if not WhisperModel:
                raise RuntimeError("faster-whisper is not installed.")
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device="auto",
                    compute_type=self.compute_type,
                )
            except Exception as e:
                # Fallback to CPU if CUDA initialization or DLLs fail
                print(f"[STT Info]: Falling back to CPU model: {e}")
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )
        return self._model

    def transcribe_audio_array(self, audio_data: np.ndarray) -> str:
        """Transcribes raw 16kHz float32 audio array with robust CPU fallback."""
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)

        try:
            segments, _ = self.model.transcribe(
                audio_data,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            return " ".join([seg.text.strip() for seg in segments]).strip()
        except Exception as err:
            # If CUDA runtime error (e.g. missing cublas64_12.dll), recreate model on CPU and retry
            print(f"[STT Warning]: Whisper execution failed ({err}), retrying on CPU...")
            try:
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8",
                )
                segments, _ = self._model.transcribe(
                    audio_data,
                    beam_size=5,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500),
                )
                return " ".join([seg.text.strip() for seg in segments]).strip()
            except Exception as cpu_err:
                print(f"[STT Error]: CPU transcription also failed: {cpu_err}")
                return ""

    def record_audio(self, duration_seconds: float = 5.0) -> Optional[np.ndarray]:
        """Records fixed-length audio buffer from default microphone."""
        if not sd:
            raise RuntimeError("sounddevice is not installed.")

        try:
            audio = sd.rec(
                int(duration_seconds * self.samplerate),
                samplerate=self.samplerate,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            return audio.flatten()
        except Exception as e:
            print(f"[Recording Error]: {e}")
            return None

    def listen_and_transcribe(self, duration_seconds: float = 5.0) -> str:
        """Records from microphone and transcribes voice input to text."""
        audio = self.record_audio(duration_seconds)
        if audio is None or len(audio) == 0:
            return ""
        return self.transcribe_audio_array(audio)
