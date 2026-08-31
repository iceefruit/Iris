"""Windows active window, process, and system contextual metadata extractor."""

import ctypes
from ctypes import wintypes, byref, c_ulong, create_unicode_buffer, Structure
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

try:
    import psutil
except ImportError:
    psutil = None


# Ensure Windows DPI awareness so coordinates and resolutions match reality
def enable_dpi_awareness() -> None:
    """Sets Per-Monitor DPI awareness to ensure accurate coordinate mapping."""
    try:
        # Per-Monitor DPI aware (V2 or V1)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


enable_dpi_awareness()


class RECT(Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


@dataclass
class WindowRect:
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int

    @classmethod
    def from_rect(cls, r: RECT) -> "WindowRect":
        return cls(
            left=r.left,
            top=r.top,
            right=r.right,
            bottom=r.bottom,
            width=max(0, r.right - r.left),
            height=max(0, r.bottom - r.top),
        )


@dataclass
class WindowContext:
    """Rich runtime metadata about what the user is currently viewing."""
    active_window_title: str
    process_name: str
    process_id: int
    window_rect: WindowRect
    screen_resolution: Tuple[int, int]
    dpi_scale: float
    visible_windows: List[str]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_window_title": self.active_window_title,
            "process_name": self.process_name,
            "process_id": self.process_id,
            "window_rect": asdict(self.window_rect),
            "screen_resolution": list(self.screen_resolution),
            "dpi_scale": self.dpi_scale,
            "visible_windows": self.visible_windows,
            "timestamp": self.timestamp,
        }

    def format_prompt_header(self) -> str:
        """Formats the context into a clean, LLM-digestible context header."""
        rect = self.window_rect
        visible_apps_str = ", ".join(self.visible_windows[:7]) if self.visible_windows else "None detected"
        dpi_percent = int(self.dpi_scale * 100)

        return (
            f"[Desktop Screen & Application Context]\n"
            f"- Active Application: {self.process_name} (PID: {self.process_id})\n"
            f"- Active Window Title: \"{self.active_window_title}\"\n"
            f"- Window Bounds: (x={rect.left}, y={rect.top}, width={rect.width}, height={rect.height})\n"
            f"- Screen Resolution: {self.screen_resolution[0]}x{self.screen_resolution[1]} (DPI Scale: {dpi_percent}%)\n"
            f"- Other Visible Applications: {visible_apps_str}\n"
            f"- Captured At: {self.timestamp}\n"
        )


class SystemContextExtractor:
    """Extracts foreground window information, screen metrics, and visible applications."""

    @staticmethod
    def get_dpi_scale() -> float:
        """Returns the system DPI scaling factor (e.g. 1.0 for 100%, 1.25 for 125%)."""
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
            if dpi > 0:
                return round(dpi / 96.0, 2)
        except Exception:
            pass
        return 1.0

    @staticmethod
    def get_screen_resolution() -> Tuple[int, int]:
        """Returns physical/virtual screen resolution (width, height)."""
        try:
            width = ctypes.windll.user32.GetSystemMetrics(0)   # SM_CXSCREEN
            height = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
            return (width, height)
        except Exception:
            return (1920, 1080)

    @classmethod
    def get_active_window_context(cls) -> WindowContext:
        """Inspects the foreground window on Windows and returns complete context."""
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()

        # Window title
        length = user32.GetWindowTextLengthW(hwnd)
        title_buf = create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        active_title = title_buf.value.strip() or "Desktop / Background"

        # PID & Process Name
        pid = c_ulong()
        user32.GetWindowThreadProcessId(hwnd, byref(pid))
        process_id = int(pid.value)
        process_name = "Unknown"

        if psutil and process_id > 0:
            try:
                proc = psutil.Process(process_id)
                process_name = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = "System / Protected"
        elif process_id > 0:
            process_name = f"PID:{process_id}"

        # Window Rect
        rect = RECT()
        user32.GetWindowRect(hwnd, byref(rect))
        window_rect = WindowRect.from_rect(rect)

        # Screen metrics & visible windows
        resolution = cls.get_screen_resolution()
        dpi_scale = cls.get_dpi_scale()
        visible_windows = cls.get_visible_windows_list(exclude_hwnd=hwnd)

        return WindowContext(
            active_window_title=active_title,
            process_name=process_name,
            process_id=process_id,
            window_rect=window_rect,
            screen_resolution=resolution,
            dpi_scale=dpi_scale,
            visible_windows=visible_windows,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @classmethod
    def get_visible_windows_list(cls, exclude_hwnd: Optional[int] = None) -> List[str]:
        """Enumerates active, visible top-level application windows."""
        user32 = ctypes.windll.user32
        visible: List[str] = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_windows_callback(hwnd, lparam):
            if hwnd == exclude_hwnd:
                return True
            if not user32.IsWindowVisible(hwnd):
                return True

            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                title_buf = create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title_buf, length + 1)
                title = title_buf.value.strip()

                # Filter out shell infrastructure windows with empty/irrelevant titles
                ignored_titles = {
                    "Program Manager",
                    "Windows Shell Experience Host",
                    "Settings",
                    "Microsoft Text Input Application",
                }
                if title and title not in ignored_titles and title not in visible:
                    visible.append(title)
            return True

        cb = WNDENUMPROC(enum_windows_callback)
        user32.EnumWindows(cb, 0)
        return visible
