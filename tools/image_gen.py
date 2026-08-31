"""Autonomous Multi-modal Image Generation Tool using Miko API."""

import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from config import config
from tools.base import BaseTool, ToolResult


class GenerateImageTool(BaseTool):
    """Tool for generating images and visual concept art via Miko API."""

    name = "generate_image"
    description = (
        "Generates images, illustrations, or concept art based on a descriptive prompt using Miko API. "
        "Supports aspect ratios: '16:9', '1:1', '9:16', '4:3', '3:4'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Detailed visual description of the image to generate.",
            },
            "size": {
                "type": "string",
                "enum": ["16:9", "1:1", "9:16", "4:3", "3:4"],
                "default": "16:9",
                "description": "Aspect ratio size (default: '16:9').",
            },
            "model": {
                "type": "string",
                "default": "qwen-image-2",
                "description": "Image generation model name (default: 'qwen-image-2').",
            },
        },
        "required": ["prompt"],
    }

    def execute(
        self, prompt: str, size: str = "16:9", model: str = "qwen-image-2", **kwargs
    ) -> ToolResult:
        clean_prompt = prompt.strip()
        if not clean_prompt:
            return ToolResult(success=False, output="", error="Prompt is empty.")

        if not config.api_key:
            return ToolResult(success=False, output="", error="MIKO_API_KEY is not configured.")

        url = f"{config.base_url.rstrip('/')}/image"
        payload = {
            "prompt": clean_prompt,
            "model": model,
            "size": size,
            "username": config.username,
            "userid": config.userid,
        }
        headers = {
            "X-API-Key": config.api_key,
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Image generation failed [{res.status_code}]: {res.text}",
                    )

                data = res.json()
                images = data.get("images", [])
                if not images:
                    return ToolResult(
                        success=False,
                        output="",
                        error="No images returned by the service.",
                    )

                cache_dir = Path(config.vision_cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)

                saved_paths = []
                for idx, img_info in enumerate(images):
                    img_url = img_info.get("url") if isinstance(img_info, dict) else str(img_info)
                    if img_url.startswith("http"):
                        # Download and save locally
                        r = client.get(img_url, timeout=30.0)
                        if r.status_code == 200:
                            local_filename = f"gen_{uuid.uuid4().hex[:8]}_{idx}.jpg"
                            local_path = cache_dir / local_filename
                            with open(local_path, "wb") as f:
                                f.write(r.content)
                            saved_paths.append(str(local_path))
                    else:
                        saved_paths.append(img_url)

                paths_str = ", ".join(saved_paths)
                return ToolResult(
                    success=True,
                    output=f"Successfully generated {len(saved_paths)} image(s) for '{clean_prompt}'. Local path(s): {paths_str}",
                )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"Image generation error: {str(e)}")
