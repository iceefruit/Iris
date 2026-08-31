"""Unit and integration test for Iris Vision Engine."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vision.context import SystemContextExtractor, WindowContext, WindowRect
from vision.capture import ScreenCaptureEngine
from vision.engine import VisionEngine


def test_context_extractor():
    print("[1] Testing SystemContextExtractor...")
    ctx = SystemContextExtractor.get_active_window_context()
    assert isinstance(ctx, WindowContext)
    assert ctx.process_name != ""
    assert ctx.window_rect.width >= 0
    assert ctx.window_rect.height >= 0
    assert ctx.dpi_scale > 0
    print(f"    Active App: {ctx.process_name} (PID: {ctx.process_id})")
    print(f"    Window Title: {ctx.active_window_title}")
    print(f"    Window Rect: {ctx.window_rect}")
    print(f"    Resolution: {ctx.screen_resolution}, DPI Scale: {ctx.dpi_scale}")
    print(f"    Visible Windows: {len(ctx.visible_windows)} found -> {ctx.visible_windows[:3]}")

    formatted_header = ctx.format_prompt_header()
    assert "[Desktop Screen & Application Context]" in formatted_header
    assert ctx.process_name in formatted_header


def test_screen_capture():
    print("\n[2] Testing ScreenCaptureEngine...")
    capturer = ScreenCaptureEngine(cache_dir=".iris_cache")
    file_path, size = capturer.capture_screen(max_dim=1280)
    
    assert Path(file_path).exists()
    assert os.path.getsize(file_path) > 0
    print(f"    Full Screen Captured: {file_path} (Dimensions: {size}, Size: {os.path.getsize(file_path)} bytes)")

    # Test cropped capture
    dummy_rect = WindowRect(left=100, top=100, right=500, bottom=400, width=400, height=300)
    crop_path, crop_size = capturer.capture_screen(crop_rect=dummy_rect)
    assert Path(crop_path).exists()
    print(f"    Cropped Captured: {crop_path} (Dimensions: {crop_size})")

    # Test coordinate normalization
    norm_x, norm_y = capturer.normalize_coordinates(960, 540, 1920, 1080)
    assert norm_x == 500
    assert norm_y == 500
    orig_x, orig_y = capturer.denormalize_coordinates(norm_x, norm_y, 1920, 1080)
    assert orig_x == 960
    assert orig_y == 540
    print("    Coordinate Normalization: (960, 540) -> [500, 500] -> (960, 540) OK")


def test_vision_engine():
    print("\n[3] Testing VisionEngine...")
    engine = VisionEngine()
    prompt, img_path, context = engine.capture_with_context(
        user_query="What is in this window?",
        crop_to_active_window=False
    )
    assert Path(img_path).exists()
    assert "What is in this window?" in prompt
    assert "[Desktop Screen & Application Context]" in prompt
    print(f"    Screenshot generated: {img_path}")


if __name__ == "__main__":
    test_context_extractor()
    test_screen_capture()
    test_vision_engine()
    print("\nAll Vision Engine Tests Passed Successfully!")
