"""Global Panic Killswitch for instant desktop actuation freeze and emergency abort."""

import threading
from typing import Callable, Optional, Any
import pyautogui

try:
    from pynput import keyboard
except ImportError:
    keyboard = None

try:
    import sounddevice as sd
except ImportError:
    sd = None


class GlobalPanicKillswitch:
    """Background hotkey listener that halts all automation when triggered."""

    def __init__(
        self,
        hotkey: str = "<ctrl>+<shift>+k",
        on_abort_callback: Optional[Callable[[], None]] = None,
    ):
        self.hotkey = hotkey
        self.on_abort_callback = on_abort_callback
        self._abort_event = threading.Event()
        self._listener: Optional[Any] = None

    @property
    def is_aborted(self) -> bool:
        return self._abort_event.is_set()

    @property
    def abort_event(self) -> threading.Event:
        return self._abort_event

    def trigger(self) -> None:
        """Invoked when the panic hotkey combination is pressed."""
        self._abort_event.set()

        # Emergency actuator cleanup: release all mouse buttons and keys
        try:
            for btn in ("left", "right", "middle"):
                pyautogui.mouseUp(button=btn)
            for key in ("ctrl", "shift", "alt", "win"):
                pyautogui.keyUp(key)
        except Exception:
            pass

        # Stop active sound playback immediately if audio is running
        if sd:
            try:
                sd.stop()
            except Exception:
                pass

        if self.on_abort_callback:
            try:
                self.on_abort_callback()
            except Exception:
                pass

    def reset(self) -> None:
        """Clears the abort flag for the next turn."""
        self._abort_event.clear()

    def start(self) -> None:
        """Starts the global hotkey daemon listener."""
        if self._listener is not None or keyboard is None:
            return

        try:
            self._listener = keyboard.GlobalHotKeys({
                self.hotkey: self.trigger
            })
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            # In headless environments or background sessions where hooks fail
            self._listener = None

    def stop(self) -> None:
        """Stops the hotkey listener."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


# Singleton instance
killswitch = GlobalPanicKillswitch()
