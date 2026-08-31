"""Unit tests for Iris Voice Subsystem (Edge-TTS and Whisper STT)."""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice.tts import EdgeTTSPlayer
from voice.stt import FasterWhisperTranscriber
from voice.engine import VoiceEngine


def test_edge_tts_synthesis():
    print("[1] Testing EdgeTTS synthesis...")
    player = EdgeTTSPlayer(voice="en-US-AvaMultilingualNeural")
    audio_bytes = asyncio.run(player._synthesize_to_bytes("Hello from Iris Desktop Assistant"))
    assert len(audio_bytes) > 1000
    print(f"    Edge-TTS generated {len(audio_bytes)} bytes of audio data.")


def test_voice_engine_initialization():
    print("\n[2] Testing VoiceEngine initialization...")
    engine = VoiceEngine()
    assert engine.tts is not None
    assert engine.stt is not None
    assert engine.stt.model_size == "base.en"
    print(f"    VoiceEngine initialized with STT model: {engine.stt.model_size}, TTS voice: {engine.tts.voice}")


if __name__ == "__main__":
    test_edge_tts_synthesis()
    test_voice_engine_initialization()
    print("\nAll Voice Engine Tests Passed Successfully!")
