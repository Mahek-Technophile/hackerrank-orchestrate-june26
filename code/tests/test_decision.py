from claim_verifier.decision import aggregate_evidence
from claim_verifier.schemas import ClaimFacet, ClaimUnderstanding, ImageAssessment, UserHistory


def _history() -> UserHistory:
    return UserHistory(
        user_id="user_x",
        past_claim_count=1,
        accept_claim=1,
        manual_review_claim=0,
        rejected_claim=0,
        last_90_days_claim_count=1,
        history_flags=["none"],
        history_summary="none",
    )


def test_supported_when_damage_and_part_visible():
    claim = ClaimUnderstanding(
        object_type="car",
        facets=[ClaimFacet("dent", "rear_bumper", "medium", 0.9)],
        primary_issue_type="dent",
        primary_object_part="rear_bumper",
        severity_hint="medium",
        explicit_multi_part_claim=False,
        summary="rear bumper dent",
        suspicious_text_present=False,
    )
    assessment = ImageAssessment(
        image_path="img.jpg",
        image_id="img_1",
        valid_image=True,
        object_present=True,
        visible_object_type="car",
        visible_object_part="rear_bumper",
        visible_issue_type="dent",
        visible_severity="medium",
        damage_visible=True,
        part_visible=True,
        view_quality="usable",
        observation_summary="Dent visible",
        support_score=0.91,
        contradiction_score=0.02,
    )
    aggregated = aggregate_evidence(claim, [assessment], _history())
    assert aggregated.claim_status == "supported"
    assert aggregated.issue_type == "dent"


def test_not_enough_information_when_part_not_visible():
    claim = ClaimUnderstanding(
        object_type="car",
        facets=[ClaimFacet("crack", "headlight", "medium", 0.9)],
        primary_issue_type="crack",
        primary_object_part="headlight",
        severity_hint="medium",
        explicit_multi_part_claim=False,
        summary="headlight crack",
        suspicious_text_present=False,
    )
    assessment = ImageAssessment(
        image_path="img.jpg",
        image_id="img_1",
        valid_image=True,
        object_present=True,
        visible_object_type="car",
        visible_object_part="door",
        visible_issue_type="scratch",
        visible_severity="low",
        damage_visible=True,
        part_visible=False,
        view_quality="usable",
        observation_summary="Wrong angle",
        support_score=0.1,
        contradiction_score=0.1,
    )
    aggregated = aggregate_evidence(claim, [assessment], _history())
    assert aggregated.claim_status == "not_enough_information"
    assert "wrong_angle" in aggregated.risk_flags
