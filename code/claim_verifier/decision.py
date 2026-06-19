from __future__ import annotations

from collections import Counter

from .schemas import AggregatedEvidence, ClaimUnderstanding, ImageAssessment, UserHistory


SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "unknown": -1}


def _normalize_risk_flags(flags: list[str]) -> list[str]:
    cleaned = sorted({flag for flag in flags if flag and flag != "none"})
    return cleaned or ["none"]


def _pick_majority(values: list[str], default: str) -> str:
    filtered = [value for value in values if value and value != "unknown"]
    return Counter(filtered).most_common(1)[0][0] if filtered else default


def _pick_severity(values: list[str], default: str) -> str:
    best = default
    best_rank = SEVERITY_ORDER.get(default, -1)
    for value in values:
        rank = SEVERITY_ORDER.get(value, -1)
        if rank > best_rank:
            best = value
            best_rank = rank
    return best


def aggregate_evidence(
    claim: ClaimUnderstanding,
    assessments: list[ImageAssessment],
    user_history: UserHistory | None,
) -> AggregatedEvidence:
    all_flags: list[str] = []
    observations: list[str] = []

    if claim.suspicious_text_present:
        all_flags.append("text_instruction_present")

    usable = [item for item in assessments if item.valid_image]
    if not usable:
        return AggregatedEvidence(
            evidence_standard_met=False,
            evidence_standard_met_reason="No submitted image could be opened reliably for review.",
            valid_image=False,
            issue_type="unknown",
            object_part=claim.primary_object_part,
            claim_status="not_enough_information",
            claim_status_justification="The submitted images are not usable for automated visual review.",
            supporting_image_ids=[],
            severity="unknown",
            risk_flags=_normalize_risk_flags(["manual_review_required"]),
            confidence=0.05,
            observations=["No valid images were available."],
        )

    for item in assessments:
        all_flags.extend(item.risk_flags)
        all_flags.extend(item.authenticity_concerns)
        if item.observation_summary:
            observations.append(f"{item.image_id}: {item.observation_summary}")

    if user_history:
        all_flags.extend(flag for flag in user_history.history_flags if flag and flag != "none")

    facet_scores: dict[tuple[str, str], dict[str, object]] = {}
    for facet in claim.facets:
        key = (facet.issue_type, facet.object_part)
        facet_scores[key] = {"support": 0.0, "contradiction": 0.0, "images": []}

    for item in usable:
        best_key = None
        best_match = -1.0
        for facet in claim.facets:
            match = 0.0
            if item.visible_issue_type == facet.issue_type:
                match += 0.55
            if item.visible_object_part == facet.object_part:
                match += 0.45
            if item.visible_object_type == claim.object_type:
                match += 0.2
            if match > best_match:
                best_match = match
                best_key = (facet.issue_type, facet.object_part)
        if best_key is None:
            continue
        facet_scores[best_key]["support"] = float(facet_scores[best_key]["support"]) + max(item.support_score, best_match)
        facet_scores[best_key]["contradiction"] = float(facet_scores[best_key]["contradiction"]) + item.contradiction_score
        if item.damage_visible and item.part_visible:
            facet_scores[best_key]["images"].append(item.image_id)

    ranked = sorted(
        facet_scores.items(),
        key=lambda kv: (float(kv[1]["support"]) - float(kv[1]["contradiction"]), float(kv[1]["support"])),
        reverse=True,
    )
    best_issue, best_part = ranked[0][0]
    best_scores = ranked[0][1]

    support_images = list(dict.fromkeys(best_scores["images"]))  # preserve order
    issue_type = best_issue if best_issue else claim.primary_issue_type
    object_part = best_part if best_part else claim.primary_object_part

    matching_images = [
        item for item in usable if item.visible_object_part == object_part or item.visible_issue_type == issue_type
    ]
    part_visible = any(item.part_visible for item in matching_images)
    damage_visible = any(item.damage_visible for item in matching_images)
    issue_majority = _pick_majority([item.visible_issue_type for item in matching_images], issue_type)
    part_majority = _pick_majority([item.visible_object_part for item in matching_images], object_part)
    severity = _pick_severity([item.visible_severity for item in matching_images], claim.severity_hint)

    support_value = float(best_scores["support"])
    contradiction_value = float(best_scores["contradiction"])
    evidence_standard_met = bool(part_visible and any(item.object_present for item in usable))

    if not evidence_standard_met:
        all_flags.extend(["damage_not_visible"])
        if not part_visible:
            all_flags.extend(["wrong_angle"])
        claim_status = "not_enough_information"
        justification = (
            f"The submitted images do not show the claimed {claim.primary_object_part} clearly enough to evaluate the claim."
        )
        evidence_reason = (
            f"The claimed {claim.primary_object_part} is not visible clearly enough to inspect the claimed condition."
        )
        severity = "unknown"
        support_images = []
    elif damage_visible and support_value >= max(0.55, contradiction_value):
        claim_status = "supported"
        justification = (
            f"The visible evidence shows {issue_majority} on the {part_majority}, which matches the reported claim."
        )
        evidence_reason = (
            f"The relevant {part_majority} is visible clearly enough to verify the claimed condition."
        )
    elif part_visible and not damage_visible:
        claim_status = "contradicted"
        issue_majority = "none"
        severity = "none"
        justification = (
            f"The relevant {part_majority} is visible, but no clear physical evidence supports the reported damage."
        )
        evidence_reason = f"The relevant {part_majority} is visible clearly enough for review."
        all_flags.extend(["damage_not_visible"])
    else:
        claim_status = "contradicted" if contradiction_value > support_value else "not_enough_information"
        justification = (
            f"The visible evidence does not align with the reported {claim.primary_issue_type} on the {claim.primary_object_part}."
        )
        evidence_reason = f"The images are reviewable, but the visible evidence does not match the reported claim."
        all_flags.extend(["claim_mismatch"])

    visible_object_types = {item.visible_object_type for item in usable if item.visible_object_type != "unknown"}
    if visible_object_types and claim.object_type not in visible_object_types:
        all_flags.extend(["wrong_object", "claim_mismatch"])
    if any(item.visible_object_part not in ("unknown", object_part) and item.part_visible for item in usable):
        all_flags.append("wrong_object_part")

    if any(flag in all_flags for flag in ("non_original_image", "possible_manipulation", "text_instruction_present")):
        all_flags.append("manual_review_required")
    if user_history and "manual_review_required" in user_history.history_flags:
        all_flags.append("manual_review_required")

    confidence = min(0.99, max(0.05, 0.25 + support_value - (0.3 * contradiction_value)))
    if claim_status == "not_enough_information":
        confidence = min(confidence, 0.45)
    if claim_status == "contradicted" and "claim_mismatch" in all_flags:
        confidence = max(confidence, 0.62)

    return AggregatedEvidence(
        evidence_standard_met=evidence_standard_met,
        evidence_standard_met_reason=evidence_reason,
        valid_image=all(item.valid_image for item in assessments),
        issue_type=issue_majority,
        object_part=part_majority,
        claim_status=claim_status,
        claim_status_justification=justification,
        supporting_image_ids=support_images,
        severity=severity if severity in ("none", "low", "medium", "high", "unknown") else "unknown",
        risk_flags=_normalize_risk_flags(all_flags),
        confidence=round(confidence, 3),
        observations=observations,
    )
