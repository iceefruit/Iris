"""High-performance screen capture and coordinate normalization engine with multi-tier fallback."""

import os
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from PIL import Image, ImageDraw

from config import config
from vision.context import WindowRect
from vision.grid import draw_coordinate_grid

try:
    import mss
    import mss.exception
except ImportError:
    mss = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None


class ScreenCaptureEngine:
    """Captures monitor or active window frames using mss / ImageGrab with graceful fallback."""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or config.vision_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def capture_screen(
        self,
        monitor_index: int = 1,
        crop_rect: Optional[Union[WindowRect, Dict[str, int]]] = None,
        max_dim: Optional[int] = None,
        quality: Optional[int] = None,
        with_grid: Optional[bool] = None,
    ) -> Tuple[str, Tuple[int, int]]:
        """Captures the screen or a cropped region and saves an optimized image.
        
        Args:
            monitor_index: Monitor index (1 = primary monitor, 0 = all monitors combined).
            crop_rect: Optional WindowRect or dict with 'left', 'top', 'width', 'height' to crop.
            max_dim: Max width/height to resize to. Defaults to config.vision_max_dimension.
            quality: JPEG quality (1-100). Defaults to config.vision_compress_quality.
            with_grid: Whether to overlay a [0, 1000] coordinate grid for visual grounding.
            
        Returns:
            Tuple of (saved_file_path, (image_width, image_height))
        """
        max_dim = max_dim or config.vision_max_dimension
        quality = quality or config.vision_compress_quality
        apply_grid = config.vision_grid_overlay if with_grid is None else with_grid
        img: Optional[Image.Image] = None

        # Strategy 1: Ultra-fast multi-monitor capture via mss
        if mss:
            try:
                with mss.mss() as sct:
                    monitors = sct.monitors
                    if monitor_index < len(monitors):
                        target_mon = monitors[monitor_index]
                    else:
                        target_mon = monitors[0]

                    if crop_rect:
                        left, top, width, height = self._parse_crop_rect(crop_rect, target_mon)
                        bbox = {
                            "left": left,
                            "top": top,
                            "width": max(10, width),
                            "height": max(10, height),
                        }
                        sct_img = sct.grab(bbox)
                    else:
                        sct_img = sct.grab(target_mon)

                    # mss raw bytes is BGRA
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception:
                img = None

        # Strategy 2: Fallback to PIL.ImageGrab
        if img is None and ImageGrab:
            try:
                bbox_tuple = None
                if crop_rect:
                    left, top, width, height = self._parse_crop_rect(crop_rect, {"left": 0, "top": 0, "width": 1920, "height": 1080})
                    bbox_tuple = (left, top, left + width, top + height)
                img = ImageGrab.grab(bbox=bbox_tuple, all_screens=True)
                if img.mode != "RGB":
                    img = img.convert("RGB")
            except Exception:
                img = None

        # Strategy 3: Graceful fallback for locked / headless / non-interactive sessions
        if img is None:
            img = self._generate_fallback_frame(crop_rect)

        # Apply visual grounding coordinate grid if requested
        if apply_grid:
            img = draw_coordinate_grid(img)

        # Downscale proportionally if exceeding max dimensions
        orig_w, orig_h = img.size
        if max_dim and (orig_w > max_dim or orig_h > max_dim):
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # Save optimized JPEG to cache
        filename = f"screen_{uuid.uuid4().hex[:10]}.jpg"
        file_path = str(self.cache_dir / filename)
        img.save(file_path, "JPEG", quality=quality, optimize=True)

        return file_path, img.size

    @staticmethod
    def _parse_crop_rect(
        crop_rect: Union[WindowRect, Dict[str, int]], target_mon: Dict[str, int]
    ) -> Tuple[int, int, int, int]:
        if isinstance(crop_rect, WindowRect):
            left = crop_rect.left
            top = crop_rect.top
            width = crop_rect.width
            height = crop_rect.height
        else:
            left = crop_rect.get("left", target_mon.get("left", 0))
            top = crop_rect.get("top", target_mon.get("top", 0))
            width = crop_rect.get("width", target_mon.get("width", 1920))
            height = crop_rect.get("height", target_mon.get("height", 1080))

        # Clamp to reasonable values
        mon_left = target_mon.get("left", 0)
        mon_top = target_mon.get("top", 0)
        mon_width = target_mon.get("width", 1920)
        mon_height = target_mon.get("height", 1080)

        left = max(mon_left, left)
        top = max(mon_top, top)
        width = min(mon_width, width)
        height = min(mon_height, height)
        return left, top, max(10, width), max(10, height)

    @staticmethod
    def _generate_fallback_frame(
        crop_rect: Optional[Union[WindowRect, Dict[str, int]]] = None
    ) -> Image.Image:
        """Generates a clean informational canvas when desktop capture is locked or unavailable."""
        width, height = 1280, 720
        img = Image.new("RGB", (width, height), color=(30, 30, 35))
        draw = ImageDraw.Draw(img)

        # Draw framing border and notice text
        draw.rectangle([(20, 20), (width - 20, height - 20)], outline=(80, 80, 100), width=2)
        draw.text(
            (width // 2 - 180, height // 2 - 20),
            "Iris Screen Capture (Desktop Locked or Background Session)",
            fill=(200, 200, 220),
        )
        return img

    @staticmethod
    def normalize_coordinates(
        x: int, y: int, screen_width: int, screen_height: int
    ) -> Tuple[int, int]:
        """Normalizes physical pixel coordinates to [0, 1000] scale."""
        norm_x = int((x / max(1, screen_width)) * 1000)
        norm_y = int((y / max(1, screen_height)) * 1000)
        return min(1000, max(0, norm_x)), min(1000, max(0, norm_y))

    @staticmethod
    def denormalize_coordinates(
        norm_x: int, norm_y: int, screen_width: int, screen_height: int
    ) -> Tuple[int, int]:
        """Converts [0, 1000] scale back to physical pixel coordinates."""
        x = int((norm_x / 1000.0) * screen_width)
        y = int((norm_y / 1000.0) * screen_height)
        return x, y

    def cleanup_cache(self, keep_last: int = 5) -> None:
        """Removes older temporary screenshot files."""
        try:
            files = sorted(
                self.cache_dir.glob("screen_*.jpg"),
                key=os.path.getmtime,
                reverse=True,
            )
            for old_file in files[keep_last:]:
                try:
                    old_file.unlink()
                except Exception:
                    pass
        except Exception:
            pass
