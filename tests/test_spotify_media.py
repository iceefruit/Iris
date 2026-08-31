"""Unit tests for Spotify, Audio Control, and Window Manager tools."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.spotify import SpotifyTool
from tools.audio_control import AudioControlTool
from tools.window_manager import WindowManagerTool
from tools.registry import default_registry


def test_spotify_tool_schema_and_actions():
    tool = SpotifyTool()
    assert tool.name == "spotify_control"
    assert "query" in tool.parameters["properties"]
    assert "action" in tool.parameters["properties"]

    with patch("pyautogui.press") as mock_press, patch("os.startfile") as mock_startfile:
        # 1. Play/Pause
        res = tool.execute(action="pause")
        assert res.success is True
        mock_press.assert_called_with("playpause")

        # 2. Next track
        res = tool.execute(action="next")
        assert res.success is True
        mock_press.assert_called_with("nexttrack")

        # 3. Previous track
        res = tool.execute(action="previous")
        assert res.success is True
        mock_press.assert_called_with("prevtrack")

        # 4. Search and Play Michael Jackson
        res = tool.execute(action="play", query="Michael Jackson")
        assert res.success is True
        assert "Michael Jackson" in res.output
        mock_startfile.assert_called_with("spotify:search:Michael%20Jackson")


def test_audio_control_tool():
    tool = AudioControlTool()
    assert tool.name == "control_volume"

    with patch("pyautogui.press") as mock_press, patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        # 1. Mute
        res = tool.execute(action="mute")
        assert res.success is True
        mock_press.assert_called_with("volumemute")

        # 2. Volume Up
        res = tool.execute(action="up", steps=3)
        assert res.success is True
        assert mock_press.call_count >= 3

        # 3. Set Volume
        res = tool.execute(action="set", level=50)
        assert res.success is True
        assert "50%" in res.output


def test_window_manager_tool():
    tool = WindowManagerTool()
    assert tool.name == "manage_window"

    with patch.object(tool, "_get_visible_windows", return_value=[(1001, "Spotify Free"), (1002, "Visual Studio Code")]):
        # 1. List
        res = tool.execute(action="list_open")
        assert res.success is True
        assert "Spotify Free" in res.output
        assert "Visual Studio Code" in res.output

        # 2. Focus Spotify
        with patch("ctypes.windll.user32.ShowWindow") as mock_show, patch("ctypes.windll.user32.SetForegroundWindow") as mock_focus:
            res = tool.execute(action="focus", window_title="Spotify")
            assert res.success is True
            assert "Focused window: 'Spotify Free'" in res.output


def test_tools_registered_in_default_registry():
    assert default_registry.get("spotify_control") is not None
    assert default_registry.get("control_volume") is not None
    assert default_registry.get("manage_window") is not None
    assert default_registry.get("browser_interact") is not None
    assert default_registry.get("send_discord_file") is not None
