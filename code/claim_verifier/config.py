from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    provider: str = "offline"
    model_name: str = "heuristic"
    root_dir: Path = Path("/workspace")
    prompt_dir: Path = Path("/workspace/code/prompts")
    cache_dir: Path = Path("/workspace/code/.cache")
    max_workers: int = 4
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    request_timeout_seconds: int = 120
    max_retries: int = 2

    @classmethod
    def from_env(cls, **overrides: object) -> "AppConfig":
        root_dir = Path(str(overrides.get("root_dir", os.getenv("CLAIM_VERIFIER_ROOT", "/workspace"))))
        prompt_dir = Path(
            str(overrides.get("prompt_dir", os.getenv("CLAIM_VERIFIER_PROMPT_DIR", root_dir / "code" / "prompts")))
        )
        cache_dir = Path(
            str(overrides.get("cache_dir", os.getenv("CLAIM_VERIFIER_CACHE_DIR", root_dir / "code" / ".cache")))
        )
        provider = str(overrides.get("provider", os.getenv("CLAIM_VERIFIER_PROVIDER", "offline"))).lower()
        model_name = str(overrides.get("model_name", os.getenv("CLAIM_VERIFIER_MODEL", "heuristic")))
        max_workers = int(overrides.get("max_workers", os.getenv("CLAIM_VERIFIER_MAX_WORKERS", "4")))
        request_timeout_seconds = int(
            overrides.get("request_timeout_seconds", os.getenv("CLAIM_VERIFIER_REQUEST_TIMEOUT", "120"))
        )
        max_retries = int(overrides.get("max_retries", os.getenv("CLAIM_VERIFIER_MAX_RETRIES", "2")))
        return cls(
            provider=provider,
            model_name=model_name,
            root_dir=root_dir,
            prompt_dir=prompt_dir,
            cache_dir=cache_dir,
            max_workers=max_workers,
            openai_api_key=str(overrides.get("openai_api_key", os.getenv("OPENAI_API_KEY") or "")) or None,
            anthropic_api_key=str(overrides.get("anthropic_api_key", os.getenv("ANTHROPIC_API_KEY") or "")) or None,
            google_api_key=str(overrides.get("google_api_key", os.getenv("GOOGLE_API_KEY") or "")) or None,
            request_timeout_seconds=request_timeout_seconds,
            max_retries=max_retries,
        )
