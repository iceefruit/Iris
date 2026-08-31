"""Vision Engine orchestrator linking screen capture with OS context."""

from typing import Optional, Tuple
from vision.context import SystemContextExtractor, WindowContext
from vision.capture import ScreenCaptureEngine


class VisionEngine:
    """Coordinates screen frame capture and active OS context injection for the AI."""

    def __init__(self):
        self.capturer = ScreenCaptureEngine()
        self.extractor = SystemContextExtractor()

    def capture_with_context(
        self,
        user_query: Optional[str] = None,
        crop_to_active_window: bool = False,
        with_grid: Optional[bool] = None,
    ) -> Tuple[str, str, WindowContext]:
        """Captures the screen and builds an enriched prompt containing OS metadata.
        
        Args:
            user_query: Optional user prompt (e.g. "What is on my screen?").
            crop_to_active_window: If True, crops screenshot strictly to foreground window.
            with_grid: If True, overlays normalized [0, 1000] coordinate grid.
            
        Returns:
            Tuple of (enriched_prompt, screenshot_path, window_context)
        """
        # 1. Extract Windows application metadata
        context = self.extractor.get_active_window_context()

        # 2. Capture screenshot (cropped or full primary screen)
        crop_rect = context.window_rect if crop_to_active_window else None
        image_path, _ = self.capturer.capture_screen(crop_rect=crop_rect, with_grid=with_grid)

        # 3. Format context header for LLM
        context_header = context.format_prompt_header()

        query_text = user_query.strip() if user_query else "Analyze what is on my screen and describe what you see."
        enriched_prompt = f"{context_header}\n[User Request]: {query_text}"

        # Clean up old cached captures to prevent disk bloat
        self.capturer.cleanup_cache(keep_last=5)

        return enriched_prompt, image_path, context
