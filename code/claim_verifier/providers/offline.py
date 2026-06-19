from __future__ import annotations

from pathlib import Path
from typing import Any

from ..schemas import ClaimUnderstanding, ImageAssessment
from .base import VisionProvider

try:
    from PIL import Image, ImageFilter, ImageStat
except ImportError:  # pragma: no cover
    Image = None
    ImageFilter = None
    ImageStat = None

try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None


class OfflineVisionProvider(VisionProvider):
    """Conservative fallback used when no external VLM is configured."""

    def assess_image(self, image_path: str, image_id: str, claim: ClaimUnderstanding) -> ImageAssessment:
        concerns: list[str] = []
        risk_flags: list[str] = []
        valid_image = False
        metadata: dict[str, Any] = {}
        observation_summary = "Offline fallback could inspect metadata but not semantic damage details."

        if Image is not None:
            try:
                with Image.open(image_path) as img:
                    valid_image = True
                    width, height = img.size
                    metadata["size"] = {"width": width, "height": height}
                    grayscale = img.convert("L")
                    if ImageStat is not None:
                        stat = ImageStat.Stat(grayscale)
                        mean_brightness = float(stat.mean[0])
                        metadata["mean_brightness"] = round(mean_brightness, 2)
                        if mean_brightness < 35:
                            risk_flags.append("low_light_or_glare")
                    if ImageFilter is not None:
                        edge_energy = ImageStat.Stat(grayscale.filter(ImageFilter.FIND_EDGES)).mean[0]
                        metadata["edge_energy"] = round(float(edge_energy), 2)
                        if edge_energy < 7:
                            risk_flags.append("blurry_image")
                    if min(width, height) < 256:
                        risk_flags.append("cropped_or_obstructed")
                    if pytesseract is not None:
                        ocr_text = pytesseract.image_to_string(img).lower()
                        metadata["ocr_excerpt"] = ocr_text[:180]
                        if "approve" in ocr_text or "skip manual review" in ocr_text:
                            risk_flags.append("text_instruction_present")
                        if any(token in ocr_text for token in ("vecteezy", "alamy", "shutterstock", "getty")):
                            concerns.append("non_original_image")
            except Exception as exc:  # pragma: no cover
                observation_summary = f"Unable to open image reliably: {exc}"
                valid_image = False

        return ImageAssessment(
            image_path=image_path,
            image_id=image_id,
            valid_image=valid_image,
            object_present=valid_image,
            visible_object_type="unknown",
            visible_object_part="unknown",
            visible_issue_type="unknown",
            visible_severity="unknown",
            damage_visible=False,
            part_visible=False,
            view_quality="usable" if valid_image else "invalid",
            authenticity_concerns=concerns,
            risk_flags=sorted(set(risk_flags)),
            observation_summary=observation_summary,
            support_score=0.0,
            contradiction_score=0.0,
            metadata=metadata,
        )
