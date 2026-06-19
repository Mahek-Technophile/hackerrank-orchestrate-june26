from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


CLAIM_STATUS_VALUES = ("supported", "contradicted", "not_enough_information")
ISSUE_TYPE_VALUES = (
    "dent",
    "scratch",
    "crack",
    "glass_shatter",
    "broken_part",
    "missing_part",
    "torn_packaging",
    "crushed_packaging",
    "water_damage",
    "stain",
    "none",
    "unknown",
)
CAR_PART_VALUES = (
    "front_bumper",
    "rear_bumper",
    "door",
    "hood",
    "windshield",
    "side_mirror",
    "headlight",
    "taillight",
    "fender",
    "quarter_panel",
    "body",
    "unknown",
)
LAPTOP_PART_VALUES = (
    "screen",
    "keyboard",
    "trackpad",
    "hinge",
    "lid",
    "corner",
    "port",
    "base",
    "body",
    "unknown",
)
PACKAGE_PART_VALUES = (
    "box",
    "package_corner",
    "package_side",
    "seal",
    "label",
    "contents",
    "item",
    "unknown",
)
RISK_FLAG_VALUES = (
    "none",
    "blurry_image",
    "cropped_or_obstructed",
    "low_light_or_glare",
    "wrong_angle",
    "wrong_object",
    "wrong_object_part",
    "damage_not_visible",
    "claim_mismatch",
    "possible_manipulation",
    "non_original_image",
    "text_instruction_present",
    "user_history_risk",
    "manual_review_required",
)
SEVERITY_VALUES = ("none", "low", "medium", "high", "unknown")
OUTPUT_COLUMNS = (
    "user_id",
    "image_paths",
    "user_claim",
    "claim_object",
    "evidence_standard_met",
    "evidence_standard_met_reason",
    "risk_flags",
    "issue_type",
    "object_part",
    "claim_status",
    "claim_status_justification",
    "supporting_image_ids",
    "valid_image",
    "severity",
)


@dataclass(slots=True)
class ClaimRow:
    user_id: str
    image_paths: list[str]
    user_claim: str
    claim_object: str
    raw_row: dict[str, str] = field(default_factory=dict)

    @property
    def image_ids(self) -> list[str]:
        return [Path(path).stem for path in self.image_paths]


@dataclass(slots=True)
class UserHistory:
    user_id: str
    past_claim_count: int
    accept_claim: int
    manual_review_claim: int
    rejected_claim: int
    last_90_days_claim_count: int
    history_flags: list[str]
    history_summary: str


@dataclass(slots=True)
class EvidenceRequirement:
    requirement_id: str
    claim_object: str
    applies_to: str
    minimum_image_evidence: str


@dataclass(slots=True)
class ClaimFacet:
    issue_type: str
    object_part: str
    severity: str
    confidence: float
    evidence_requirements: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass(slots=True)
class ClaimUnderstanding:
    object_type: str
    facets: list[ClaimFacet]
    primary_issue_type: str
    primary_object_part: str
    severity_hint: str
    explicit_multi_part_claim: bool
    summary: str
    suspicious_text_present: bool


@dataclass(slots=True)
class ImageAssessment:
    image_path: str
    image_id: str
    valid_image: bool
    object_present: bool
    visible_object_type: str
    visible_object_part: str
    visible_issue_type: str
    visible_severity: str
    damage_visible: bool
    part_visible: bool
    view_quality: str
    authenticity_concerns: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    observation_summary: str = ""
    support_score: float = 0.0
    contradiction_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AggregatedEvidence:
    evidence_standard_met: bool
    evidence_standard_met_reason: str
    valid_image: bool
    issue_type: str
    object_part: str
    claim_status: str
    claim_status_justification: str
    supporting_image_ids: list[str]
    severity: str
    risk_flags: list[str]
    confidence: float
    observations: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OutputRow:
    user_id: str
    image_paths: str
    user_claim: str
    claim_object: str
    evidence_standard_met: str
    evidence_standard_met_reason: str
    risk_flags: str
    issue_type: str
    object_part: str
    claim_status: str
    claim_status_justification: str
    supporting_image_ids: str
    valid_image: str
    severity: str

    def as_dict(self) -> dict[str, str]:
        return {
            "user_id": self.user_id,
            "image_paths": self.image_paths,
            "user_claim": self.user_claim,
            "claim_object": self.claim_object,
            "evidence_standard_met": self.evidence_standard_met,
            "evidence_standard_met_reason": self.evidence_standard_met_reason,
            "risk_flags": self.risk_flags,
            "issue_type": self.issue_type,
            "object_part": self.object_part,
            "claim_status": self.claim_status,
            "claim_status_justification": self.claim_status_justification,
            "supporting_image_ids": self.supporting_image_ids,
            "valid_image": self.valid_image,
            "severity": self.severity,
        }
