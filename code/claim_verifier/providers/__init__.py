from __future__ import annotations

from ..config import AppConfig
from .base import VisionProvider
from .offline import OfflineVisionProvider
from .openai_provider import OpenAIVisionProvider


def build_provider(config: AppConfig) -> VisionProvider:
    if config.provider == "offline":
        return OfflineVisionProvider()
    if config.provider == "openai":
        return OpenAIVisionProvider(config)
    raise ValueError(f"Unsupported provider: {config.provider}")
