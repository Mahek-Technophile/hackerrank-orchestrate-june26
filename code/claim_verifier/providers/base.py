from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import ClaimUnderstanding, ImageAssessment


class VisionProvider(ABC):
    @abstractmethod
    def assess_image(self, image_path: str, image_id: str, claim: ClaimUnderstanding) -> ImageAssessment:
        raise NotImplementedError
