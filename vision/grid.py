"""Coordinate Grid Overlay and Visual Grounding (Set-of-Marks) generator."""

from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont


def draw_coordinate_grid(
    image: Image.Image,
    step: int = 100,
    line_alpha: int = 70,
    grid_color: Tuple[int, int, int] = (0, 220, 255),
    text_color: Tuple[int, int, int] = (255, 255, 255),
    show_intersections: bool = True,
) -> Image.Image:
    """Renders a semi-transparent normalized [0, 1000] coordinate grid onto the image.
    
    Args:
        image: Source PIL Image.
        step: Step size in normalized [0, 1000] units (default 100 = 10x10 grid).
        line_alpha: Alpha transparency (0-255) for grid lines.
        grid_color: RGB tuple for grid lines (default cyan).
        text_color: RGB tuple for coordinate labels.
        show_intersections: Whether to draw coordinate text badges at grid intersections.
        
    Returns:
        New PIL Image with coordinate grid overlay composited.
    """
    img_rgb = image.convert("RGBA")
    overlay = Image.new("RGBA", img_rgb.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = img_rgb.size
    line_rgba = (*grid_color, line_alpha)
    accent_rgba = (255, 80, 80, min(255, line_alpha + 50))

    font = ImageFont.load_default()

    # Draw vertical lines (X-axis steps from 0 to 1000)
    for norm_x in range(step, 1000, step):
        px_x = int((norm_x / 1000.0) * w)
        color = accent_rgba if norm_x == 500 else line_rgba
        width = 2 if norm_x == 500 else 1
        draw.line([(px_x, 0), (px_x, h)], fill=color, width=width)

        # X header label at top
        tag = f"x={norm_x}"
        draw.rectangle([(px_x - 18, 4), (px_x + 18, 16)], fill=(20, 20, 25, 200))
        draw.text((px_x - 14, 4), tag, fill=text_color, font=font)

    # Draw horizontal lines (Y-axis steps from 0 to 1000)
    for norm_y in range(step, 1000, step):
        px_y = int((norm_y / 1000.0) * h)
        color = accent_rgba if norm_y == 500 else line_rgba
        width = 2 if norm_y == 500 else 1
        draw.line([(0, px_y), (w, px_y)], fill=color, width=width)

        # Y margin label at left
        tag = f"y={norm_y}"
        draw.rectangle([(4, px_y - 7), (40, px_y + 7)], fill=(20, 20, 25, 200))
        draw.text((6, px_y - 6), tag, fill=text_color, font=font)

    # Draw intersection markers for high-precision grounding
    if show_intersections:
        for norm_y in range(step * 2, 1000, step * 2):
            for norm_x in range(step * 2, 1000, step * 2):
                px_x = int((norm_x / 1000.0) * w)
                px_y = int((norm_y / 1000.0) * h)

                # Draw point badge
                draw.rectangle(
                    [(px_x - 22, px_y - 7), (px_x + 22, px_y + 7)],
                    fill=(15, 15, 20, 180),
                    outline=(*grid_color, 180),
                    width=1,
                )
                draw.text(
                    (px_x - 19, px_y - 6),
                    f"{norm_x},{norm_y}",
                    fill=text_color,
                    font=font,
                )

    # Center marker (500, 500)
    center_x, center_y = int(w * 0.5), int(h * 0.5)
    draw.ellipse(
        [(center_x - 5, center_y - 5), (center_x + 5, center_y + 5)],
        fill=(255, 50, 50, 230),
    )

    # Composite overlay onto original image
    composited = Image.alpha_composite(img_rgb, overlay)
    return composited.convert("RGB")
