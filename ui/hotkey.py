"""Global Background Hotkey Manager for toggling Iris HUD."""

import threading
from typing import Optional
from PySide6.QtCore import QObject, Signal
from pynput import keyboard
from config import config


class UIHotkeySignals(QObject):
    toggle_hud = Signal()


class GlobalUIHotkeyListener:
    """Listens for global shortcut (default: Ctrl+Shift+T) and safely emits Qt signals."""

    def __init__(self, hotkey_str: Optional[str] = None):
        self.hotkey_str = hotkey_str or config.ui_hotkey
        self.signals = UIHotkeySignals()
        self._listener: Optional[keyboard.GlobalHotKeys] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts background global hotkey listener."""
        if self._listener is not None:
            return

        def _on_hotkey_activated():
            self.signals.toggle_hud.emit()

        try:
            hotkey_map = {self.hotkey_str: _on_hotkey_activated}
            self._listener = keyboard.GlobalHotKeys(hotkey_map)
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            print(f"[UI Hotkey Listener Warning]: Could not bind hotkey {self.hotkey_str}: {e}")

    def stop(self) -> None:
        """Stops background hotkey listener."""
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
