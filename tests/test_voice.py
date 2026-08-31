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


from voice.listener import extract_wake_word_query, is_acoustic_echo


def test_wake_word_extraction():
    print("\n[3] Testing Wake-Word Detection & Cleaning...")
    # Case 1: "Hey Iris, play Michael Jackson"
    q1 = extract_wake_word_query("Hey Iris, play Michael Jackson on Spotify", "iris")
    assert q1 == "play Michael Jackson on Spotify"

    # Case 2: "Ok Iris, what is on my screen?"
    q2 = extract_wake_word_query("Ok Iris, what is on my screen?", "iris")
    assert q2 == "what is on my screen?"

    # Case 3: Just "Iris"
    q3 = extract_wake_word_query("Iris", "iris")
    assert q3 == "Hello Iris"

    # Case 4: No wake word
    q4 = extract_wake_word_query("Random chatter between friends", "iris")
    assert q4 is None
    print("    Wake-word extraction passed!")


def test_acoustic_echo_filter():
    last_spoken = "The current time is 7:35 PM and your CPU usage is 24 percent."
    
    # Substring echo
    assert is_acoustic_echo("time is 7:35 PM", last_spoken) is True
    assert is_acoustic_echo("your CPU usage is 24 percent", last_spoken) is True
    
    # Exact echo
    assert is_acoustic_echo(last_spoken, last_spoken) is True
    
    # Real follow up from user
    assert is_acoustic_echo("What about my RAM?", last_spoken) is False
    assert is_acoustic_echo("Can you open Spotify?", last_spoken) is False


if __name__ == "__main__":
    test_edge_tts_synthesis()
    test_voice_engine_initialization()
    test_wake_word_extraction()
    print("\nAll Voice Engine Tests Passed Successfully!")
