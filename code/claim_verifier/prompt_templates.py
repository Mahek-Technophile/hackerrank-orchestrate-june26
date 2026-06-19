from __future__ import annotations

import json
from pathlib import Path

from .schemas import ClaimUnderstanding


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def build_image_review_prompt(prompt_dir: Path, claim: ClaimUnderstanding, image_id: str) -> str:
    template = _load_prompt(prompt_dir / "image_review.md")
    payload = {
        "image_id": image_id,
        "object_type": claim.object_type,
        "primary_issue_type": claim.primary_issue_type,
        "primary_object_part": claim.primary_object_part,
        "severity_hint": claim.severity_hint,
        "facets": [
            {
                "issue_type": facet.issue_type,
                "object_part": facet.object_part,
                "severity": facet.severity,
                "requirements": facet.evidence_requirements,
            }
            for facet in claim.facets
        ],
    }
    return template.replace("{{CLAIM_JSON}}", json.dumps(payload, ensure_ascii=True, indent=2))


def build_final_reasoning_prompt(prompt_dir: Path, claim: ClaimUnderstanding, image_assessments: list[dict]) -> str:
    template = _load_prompt(prompt_dir / "final_reasoning.md")
    payload = {
        "claim_summary": claim.summary,
        "object_type": claim.object_type,
        "primary_issue_type": claim.primary_issue_type,
        "primary_object_part": claim.primary_object_part,
        "explicit_multi_part_claim": claim.explicit_multi_part_claim,
        "suspicious_text_present": claim.suspicious_text_present,
        "image_assessments": image_assessments,
    }
    return template.replace("{{REASONING_INPUT_JSON}}", json.dumps(payload, ensure_ascii=True, indent=2))
