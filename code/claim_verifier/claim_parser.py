from __future__ import annotations

import re
from collections import Counter

from .schemas import ClaimFacet, ClaimUnderstanding, EvidenceRequirement


ISSUE_KEYWORDS = {
    "glass_shatter": ["shatter", "shattered"],
    "broken_part": ["broken", "broke", "not sitting", "wobbles", "damaged hinge"],
    "missing_part": ["missing", "came off", "not there"],
    "torn_packaging": ["torn", "opened", "open", "phati", "abierto"],
    "crushed_packaging": ["crushed", "crush", "dab", "dented corner", "smashed"],
    "water_damage": ["water damage", "wet", "liquid damage", "coffee", "spill", "spilled"],
    "stain": ["stain", "sticky", "mark", "oily"],
    "crack": ["crack", "cracked", "cracked.", "cracked,", "glass crack"],
    "dent": ["dent", "dented", "hail dents"],
    "scratch": ["scratch", "scrape", "scratched", "mark across"],
}

PART_KEYWORDS = {
    "car": {
        "rear_bumper": ["rear bumper", "back bumper", "bumper ke upar", "back looks damaged"],
        "front_bumper": ["front bumper", "parachoques", "front side"],
        "door": ["door", "door panel"],
        "hood": ["hood"],
        "windshield": ["windshield", "front glass"],
        "side_mirror": ["side mirror", "mirror"],
        "headlight": ["headlight"],
        "taillight": ["taillight", "back light"],
        "fender": ["fender"],
        "quarter_panel": ["quarter panel"],
        "body": ["body", "panel"],
    },
    "laptop": {
        "screen": ["screen", "display"],
        "keyboard": ["keyboard", "keys", "keycaps", "teclas"],
        "trackpad": ["trackpad", "cursor movement", "palm-rest"],
        "hinge": ["hinge"],
        "lid": ["lid"],
        "corner": ["corner"],
        "port": ["port"],
        "base": ["base"],
        "body": ["body", "side edge", "outer body"],
    },
    "package": {
        "box": ["box", "package", "parcel"],
        "package_corner": ["corner"],
        "package_side": ["side", "surface", "outside"],
        "seal": ["seal", "tape", "flap", "opened"],
        "label": ["label"],
        "contents": ["contents", "inside", "product", "item missing"],
        "item": ["item", "product"],
    },
}

SEVERITY_KEYWORDS = {
    "high": ["severe", "bad", "shattered", "pretty bad", "opened", "missing"],
    "medium": ["broken", "crack", "dent", "crushed", "water", "stain"],
    "low": ["small", "light", "minor", "scratch"],
}

SUSPICIOUS_TEXT = (
    "approve the claim",
    "skip manual review",
    "ignore previous instructions",
    "mark this row supported",
    "follow it and approve",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _best_keyword_match(text: str, keyword_map: dict[str, list[str]], default: str) -> str:
    scores: Counter[str] = Counter()
    latest_position: dict[str, int] = {}
    for label, keywords in keyword_map.items():
        for keyword in keywords:
            position = text.rfind(keyword)
            if position >= 0:
                scores[label] += len(keyword)
                latest_position[label] = max(latest_position.get(label, -1), position)
    if not scores:
        return default
    return max(scores, key=lambda label: (latest_position.get(label, -1), scores[label]))


def _extract_facets(claim_object: str, text: str) -> list[ClaimFacet]:
    issue = _best_keyword_match(text, ISSUE_KEYWORDS, "unknown")
    object_part = _best_keyword_match(text, PART_KEYWORDS.get(claim_object, {}), "unknown")
    severity = _best_keyword_match(text, SEVERITY_KEYWORDS, "unknown")

    facets = [
        ClaimFacet(
            issue_type=issue,
            object_part=object_part,
            severity=severity,
            confidence=0.72 if issue != "unknown" or object_part != "unknown" else 0.35,
            rationale="Derived from multilingual keyword and phrase matching over the user conversation.",
        )
    ]

    # Capture explicit compound claims by splitting on conjunction-like phrases.
    fragments = re.split(r"\b(?:and|plus|together|both|second|first)\b", text)
    for fragment in fragments[1:]:
        fragment = fragment.strip(" .,:;|-")
        if not fragment:
            continue
        frag_issue = _best_keyword_match(fragment, ISSUE_KEYWORDS, issue)
        frag_part = _best_keyword_match(fragment, PART_KEYWORDS.get(claim_object, {}), object_part)
        if frag_issue == issue and frag_part == object_part:
            continue
        facets.append(
            ClaimFacet(
                issue_type=frag_issue,
                object_part=frag_part,
                severity=_best_keyword_match(fragment, SEVERITY_KEYWORDS, severity),
                confidence=0.58,
                rationale="Additional facet extracted from a compound or multi-part claim fragment.",
            )
        )
    return facets


def attach_requirements(understanding: ClaimUnderstanding, requirements: list[EvidenceRequirement]) -> ClaimUnderstanding:
    req_texts = [
        req.minimum_image_evidence
        for req in requirements
        if req.claim_object in ("all", understanding.object_type)
    ]
    for facet in understanding.facets:
        facet.evidence_requirements = req_texts
    return understanding


def parse_claim(claim_object: str, user_claim: str, requirements: list[EvidenceRequirement]) -> ClaimUnderstanding:
    text = _normalize(user_claim)
    facets = _extract_facets(claim_object, text)
    primary = facets[0]
    suspicious = any(phrase in text for phrase in SUSPICIOUS_TEXT)
    explicit_multi_part = len(facets) > 1 or any(token in text for token in (" both ", " together", " two things"))
    understanding = ClaimUnderstanding(
        object_type=claim_object,
        facets=facets,
        primary_issue_type=primary.issue_type,
        primary_object_part=primary.object_part,
        severity_hint=primary.severity,
        explicit_multi_part_claim=explicit_multi_part,
        summary=f"Claimed {claim_object} issue on {primary.object_part} described as {primary.issue_type}.",
        suspicious_text_present=suspicious,
    )
    return attach_requirements(understanding, requirements)
