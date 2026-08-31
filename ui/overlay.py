"""Moody Wavy Blue Gradient Fullscreen Voice Listening Overlay with Glassmorphic Status Pill."""

import math
import sys
from typing import Optional
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QPainter,
    QColor,
    QLinearGradient,
    QRadialGradient,
    QPainterPath,
    QFont,
    QPen,
    QBrush,
    QGuiApplication,
)
from PySide6.QtWidgets import QWidget

# Windows Win32 click-through flags
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000


class VoiceListeningOverlay(QWidget):
    """Fullscreen click-through overlay with a moody wavy dissolving blue border and top status pill."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Frameless, transparent, stays on top, tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Visual state
        self.current_state = "idle"  # "listening", "thinking", "speaking", "idle"
        self.status_text = "Iris is listening..."
        self.phase = 0.0
        self.current_opacity = 0.0
        self.target_opacity = 0.0
        self.is_active = False

        # Configuration
        self.border_base_thickness = 28.0  # Thin & elegant
        self.pill_width = 240
        self.pill_height = 42

        # 60 FPS animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(16)  # ~60 FPS
        self.anim_timer.timeout.connect(self._on_animation_frame)
        self.anim_timer.start()

        self._update_geometry_to_screen()

    def _update_geometry_to_screen(self) -> None:
        """Covers the entire primary screen."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.setGeometry(geo)

    def _apply_click_through(self) -> None:
        """Makes the window click-through so user can continue clicking their applications."""
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
            except Exception:
                pass

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_click_through()

    def set_listening_state(self, state: str, custom_text: Optional[str] = None) -> None:
        """Transitions state between 'listening', 'thinking', 'speaking', and 'idle'."""
        self.current_state = state.lower()
        if self.current_state in ("listening", "listen"):
            self.is_active = True
            self.target_opacity = 1.0
            self.status_text = custom_text or "Iris is listening..."
            self._update_geometry_to_screen()
            self.show()
            self._apply_click_through()
        elif self.current_state in ("thinking", "reasoning"):
            self.is_active = True
            self.target_opacity = 1.0
            self.status_text = custom_text or "Iris is thinking..."
        elif self.current_state in ("speaking", "speak"):
            self.is_active = True
            self.target_opacity = 1.0
            self.status_text = custom_text or "Iris is speaking..."
        else:  # idle / hide
            self.is_active = False
            self.target_opacity = 0.0

    def _on_animation_frame(self) -> None:
        """Updates wave phase and smooth opacity fading."""
        # 1. Update wave phase
        self.phase = (self.phase + 0.045) % (math.pi * 2000.0)

        # 2. Smoothly ease opacity (fade in / dissolve out)
        diff = self.target_opacity - self.current_opacity
        if abs(diff) > 0.01:
            self.current_opacity += diff * 0.12
            self.update()
        elif self.target_opacity == 0.0 and self.current_opacity <= 0.01:
            if self.isVisible():
                self.current_opacity = 0.0
                self.hide()
        elif self.is_active or self.current_opacity > 0.01:
            self.update()

    def paintEvent(self, event) -> None:
        if self.current_opacity <= 0.005:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setOpacity(self.current_opacity)

        w = float(self.width())
        h = float(self.height())

        # 1. Draw Moody Wavy Dissolving Blue Gradient Border
        self._draw_wavy_gradient_border(painter, w, h)

        # 2. Draw Glassmorphic Top Status Pill
        self._draw_status_pill(painter, w, h)

        painter.end()

    def _draw_wavy_gradient_border(self, painter: QPainter, w: float, h: float) -> None:
        """Renders 4 organic, wavy dissolving gradient borders around screen edges."""
        # Dynamic sine wave breathing pulse
        pulse = 0.78 + 0.22 * math.sin(self.phase * 2.2)
        wave_thickness = self.border_base_thickness * (0.90 + 0.20 * math.sin(self.phase * 1.5))

        # Color palette depending on state
        if self.current_state in ("thinking", "reasoning"):
            # Indigo / Electric Purple-Blue shimmer
            c_core = QColor(99, 102, 241, int(190 * pulse))
            c_mid = QColor(56, 189, 248, int(110 * pulse))
        elif self.current_state in ("speaking", "speak"):
            # Azure / Cyan acoustic glow
            c_core = QColor(14, 165, 233, int(210 * pulse))
            c_mid = QColor(56, 189, 248, int(130 * pulse))
        else:
            # Listening: Ethereal Electric Cyan / Azure
            c_core = QColor(6, 182, 212, int(200 * pulse))
            c_mid = QColor(56, 189, 248, int(120 * pulse))

        c_transparent = QColor(14, 165, 233, 0)

        # TOP BORDER GRADIENT
        grad_top = QLinearGradient(0, 0, 0, wave_thickness)
        grad_top.setColorAt(0.0, c_core)
        grad_top.setColorAt(0.35, c_mid)
        grad_top.setColorAt(1.0, c_transparent)
        painter.fillRect(QRectF(0, 0, w, wave_thickness), QBrush(grad_top))

        # BOTTOM BORDER GRADIENT
        grad_bottom = QLinearGradient(0, h, 0, h - wave_thickness)
        grad_bottom.setColorAt(0.0, c_core)
        grad_bottom.setColorAt(0.35, c_mid)
        grad_bottom.setColorAt(1.0, c_transparent)
        painter.fillRect(QRectF(0, h - wave_thickness, w, wave_thickness), QBrush(grad_bottom))

        # LEFT BORDER GRADIENT
        grad_left = QLinearGradient(0, 0, wave_thickness, 0)
        grad_left.setColorAt(0.0, c_core)
        grad_left.setColorAt(0.35, c_mid)
        grad_left.setColorAt(1.0, c_transparent)
        painter.fillRect(QRectF(0, 0, wave_thickness, h), QBrush(grad_left))

        # RIGHT BORDER GRADIENT
        grad_right = QLinearGradient(w, 0, w - wave_thickness, 0)
        grad_right.setColorAt(0.0, c_core)
        grad_right.setColorAt(0.35, c_mid)
        grad_right.setColorAt(1.0, c_transparent)
        painter.fillRect(QRectF(w - wave_thickness, 0, wave_thickness, h), QBrush(grad_right))

        # CORNER RADIAL GLOWS FOR SMOOTH DISSOLVE
        corners = [
            (0, 0, 0, 0),
            (w, 0, w, 0),
            (0, h, 0, h),
            (w, h, w, h),
        ]
        corner_r = wave_thickness * 1.5
        for cx, cy, fx, fy in corners:
            rg = QRadialGradient(cx, cy, corner_r, fx, fy)
            rg.setColorAt(0.0, c_core)
            rg.setColorAt(0.4, c_mid)
            rg.setColorAt(1.0, c_transparent)
            painter.fillRect(
                QRectF(cx - corner_r if cx > 0 else 0, cy - corner_r if cy > 0 else 0, corner_r, corner_r),
                QBrush(rg),
            )

    def _draw_status_pill(self, painter: QPainter, w: float, h: float) -> None:
        """Renders the top glassmorphic status capsule."""
        pill_x = (w - self.pill_width) / 2.0
        pill_y = 22.0

        pill_rect = QRectF(pill_x, pill_y, self.pill_width, self.pill_height)

        # 1. Pill Background with subtle glassmorphic backdrop
        path = QPainterPath()
        path.addRoundedRect(pill_rect, self.pill_height / 2.0, self.pill_height / 2.0)

        # Subtle dark glass background
        bg_color = QColor(10, 15, 29, 225)
        painter.fillPath(path, QBrush(bg_color))

        # 2. Glowing Pill Border
        border_pulse = 0.8 + 0.2 * math.sin(self.phase * 3.0)
        if self.current_state in ("thinking", "reasoning"):
            border_color = QColor(168, 85, 247, int(200 * border_pulse))
        elif self.current_state in ("speaking", "speak"):
            border_color = QColor(56, 189, 248, int(220 * border_pulse))
        else:
            border_color = QColor(6, 182, 212, int(210 * border_pulse))

        pen = QPen(border_color, 1.4)
        painter.strokePath(path, pen)

        # 3. Animated Icon / Waveform on the left
        icon_x = pill_x + 18
        icon_y = pill_y + self.pill_height / 2.0

        if self.current_state in ("speaking", "speak"):
            # 3 Animated Audio Wave Bars
            for i in range(3):
                bar_h = 6 + 9 * abs(math.sin(self.phase * 4.0 + i * 1.2))
                bx = icon_x + i * 5
                painter.fillRect(
                    QRectF(bx, icon_y - bar_h / 2.0, 2.8, bar_h),
                    QBrush(QColor(56, 189, 248)),
                )
        elif self.current_state in ("thinking", "reasoning"):
            # Spinning / Pulsing Energy Dot
            dot_r = 4.0 + 1.8 * math.sin(self.phase * 5.0)
            painter.setBrush(QBrush(QColor(168, 85, 247)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(icon_x + 6, icon_y), dot_r, dot_r)
        else:
            # Listening: Pulsing Cyan Core Dot with Ripple
            glow_r = 3.5 + 2.0 * math.sin(self.phase * 3.5)
            painter.setBrush(QBrush(QColor(6, 182, 212)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(icon_x + 6, icon_y), glow_r, glow_r)

        # 4. Status Text
        painter.setPen(QColor(241, 245, 249))
        font = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        painter.setFont(font)

        text_rect = QRectF(pill_x + 36, pill_y, self.pill_width - 44, self.pill_height)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.status_text)
