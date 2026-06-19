from __future__ import annotations

import base64
import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path

from ..config import AppConfig
from ..prompt_templates import build_image_review_prompt
from ..schemas import ClaimUnderstanding, ImageAssessment
from .base import VisionProvider


def _read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def _data_uri(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".") or "jpeg"
    mime_type = "image/jpeg" if suffix == "jpg" else f"image/{suffix}"
    return f"data:{mime_type};base64,{base64.b64encode(_read_bytes(path)).decode('ascii')}"


def _parse_json_text(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    return json.loads(cleaned)


class OpenAIVisionProvider(VisionProvider):
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, config: AppConfig) -> None:
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for provider=openai")
        self.config = config
        self.cache_dir = config.cache_dir / "openai"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, image_path: str, claim: ClaimUnderstanding) -> str:
        digest = hashlib.sha256()
        digest.update(_read_bytes(image_path))
        digest.update(json.dumps(asdict(claim), sort_keys=True).encode("utf-8"))
        digest.update(self.config.model_name.encode("utf-8"))
        return digest.hexdigest()

    def _call_api(self, prompt: str, image_path: str) -> dict:
        payload = {
            "model": self.config.model_name,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You are a careful multimodal insurance evidence reviewer. "
                                "Return strict JSON only. Separate observations from assumptions. "
                                "Use only allowed labels and be conservative when evidence is weak."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": _data_uri(image_path)}},
                    ],
                },
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            request = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.config.request_timeout_seconds) as response:
                    result = json.loads(response.read().decode("utf-8"))
                text = result["choices"][0]["message"]["content"]
                return _parse_json_text(text)
            except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt >= self.config.max_retries:
                    break
                time.sleep(2**attempt)
        raise RuntimeError(f"OpenAI vision call failed: {last_error}")

    def assess_image(self, image_path: str, image_id: str, claim: ClaimUnderstanding) -> ImageAssessment:
        cache_key = self._cache_key(image_path, claim)
        cache_path = self.cache_dir / f"{cache_key}.json"
        if cache_path.exists():
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            prompt = build_image_review_prompt(self.config.prompt_dir, claim, image_id)
            data = self._call_api(prompt, image_path)
            cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")

        return ImageAssessment(
            image_path=image_path,
            image_id=image_id,
            valid_image=bool(data.get("valid_image", True)),
            object_present=bool(data.get("object_present", True)),
            visible_object_type=str(data.get("visible_object_type", "unknown")),
            visible_object_part=str(data.get("visible_object_part", "unknown")),
            visible_issue_type=str(data.get("visible_issue_type", "unknown")),
            visible_severity=str(data.get("visible_severity", "unknown")),
            damage_visible=bool(data.get("damage_visible", False)),
            part_visible=bool(data.get("part_visible", False)),
            view_quality=str(data.get("view_quality", "usable")),
            authenticity_concerns=[str(item) for item in data.get("authenticity_concerns", [])],
            risk_flags=[str(item) for item in data.get("risk_flags", [])],
            observation_summary=str(data.get("observation_summary", "")),
            support_score=float(data.get("support_score", 0.0)),
            contradiction_score=float(data.get("contradiction_score", 0.0)),
            metadata={"raw_response": data},
        )
