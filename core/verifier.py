"""Visual Action Verifier and Screen State Diffing Engine for Iris."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageChops, ImageStat


class ActionVisualOutcome(str, Enum):
    SUCCESS_CHANGED = "SUCCESS_CHANGED"       # Expected localized UI response (0.1% - 40% change)
    NO_EFFECT_STATIC = "NO_EFFECT_STATIC"     # No visual change detected (< 0.1% change)
    MODAL_OR_REFRESH = "MODAL_OR_REFRESH"     # Large-scale screen update or modal (> 40% change)
    ERROR_OCCURRED = "ERROR_OCCURRED"         # Image comparison failure


@dataclass
class VerificationResult:
    outcome: ActionVisualOutcome
    change_ratio: float
    changed_bbox: Optional[Tuple[int, int, int, int]] = None
    observation: str = ""
    suggested_action: str = ""


class VisualActionVerifier:
    """Compares pre-action and post-action screenshots to verify actuation success."""

    @staticmethod
    def verify(
        before_image_path: str,
        after_image_path: str,
        expected_tool: str = "",
    ) -> VerificationResult:
        """Computes pixel delta and categorizes visual state outcome."""
        try:
            p_before = Path(before_image_path)
            p_after = Path(after_image_path)

            if not p_before.exists() or not p_after.exists():
                return VerificationResult(
                    outcome=ActionVisualOutcome.ERROR_OCCURRED,
                    change_ratio=0.0,
                    observation="One or both screenshot files not found for verification.",
                )

            with Image.open(p_before).convert("RGB") as img1, Image.open(p_after).convert("RGB") as img2:
                # Ensure dimensions match
                if img1.size != img2.size:
                    img2 = img2.resize(img1.size)

                # Compute difference image
                diff = ImageChops.difference(img1, img2)
                stat = ImageStat.Stat(diff)
                # Average channel difference (0 to 255)
                avg_diff = sum(stat.mean) / len(stat.mean)
                change_ratio = avg_diff / 255.0

                bbox = diff.getbbox()

                # Categorize
                if change_ratio < 0.002:  # Less than 0.2% change
                    return VerificationResult(
                        outcome=ActionVisualOutcome.NO_EFFECT_STATIC,
                        change_ratio=round(change_ratio, 4),
                        changed_bbox=bbox,
                        observation=(
                            f"Action '{expected_tool}' produced NO visual change on screen "
                            f"(diff ratio: {round(change_ratio * 100, 2)}%)."
                        ),
                        suggested_action=(
                            "The element may be inactive, covered by another window, or require "
                            "adjusted coordinates or a double-click."
                        ),
                    )

                elif change_ratio > 0.35:  # Over 35% screen changed
                    return VerificationResult(
                        outcome=ActionVisualOutcome.MODAL_OR_REFRESH,
                        change_ratio=round(change_ratio, 4),
                        changed_bbox=bbox,
                        observation=(
                            f"Action triggered a major screen change or modal dialog "
                            f"(diff ratio: {round(change_ratio * 100, 2)}%)."
                        ),
                        suggested_action="Inspect the new window or dialog state before proceeding.",
                    )

                else:
                    return VerificationResult(
                        outcome=ActionVisualOutcome.SUCCESS_CHANGED,
                        change_ratio=round(change_ratio, 4),
                        changed_bbox=bbox,
                        observation=(
                            f"Action '{expected_tool}' succeeded with localized visual update "
                            f"(diff ratio: {round(change_ratio * 100, 2)}%)."
                        ),
                        suggested_action="Proceed with the next step towards the goal.",
                    )

        except Exception as e:
            return VerificationResult(
                outcome=ActionVisualOutcome.ERROR_OCCURRED,
                change_ratio=0.0,
                observation=f"Verification error: {str(e)}",
            )
