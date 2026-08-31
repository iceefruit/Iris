"""Vision engine package for Iris."""

from vision.context import (
    WindowContext,
    WindowRect,
    SystemContextExtractor,
    enable_dpi_awareness,
)
from vision.capture import ScreenCaptureEngine
from vision.grid import draw_coordinate_grid
from vision.engine import VisionEngine

__all__ = [
    "VisionEngine",
    "ScreenCaptureEngine",
    "SystemContextExtractor",
    "WindowContext",
    "WindowRect",
    "enable_dpi_awareness",
    "draw_coordinate_grid",
]
