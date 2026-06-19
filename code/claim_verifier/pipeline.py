from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .claim_parser import parse_claim
from .config import AppConfig
from .decision import aggregate_evidence
from .providers import build_provider
from .schemas import ClaimRow, OutputRow, UserHistory


class ClaimVerificationPipeline:
    def __init__(self, config: AppConfig, requirements: list, user_histories: dict[str, UserHistory]) -> None:
        self.config = config
        self.requirements = requirements
        self.user_histories = user_histories
        self.provider = build_provider(config)

    def _assess_images(self, claim_row: ClaimRow, claim_understanding):
        def _run(image_path: str):
            image_id = image_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            return self.provider.assess_image(image_path, image_id, claim_understanding)

        max_workers = max(1, min(self.config.max_workers, len(claim_row.image_paths) or 1))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(_run, claim_row.image_paths))

    def predict_row(self, claim_row: ClaimRow) -> tuple[OutputRow, dict]:
        claim_understanding = parse_claim(
            claim_object=claim_row.claim_object,
            user_claim=claim_row.user_claim,
            requirements=self.requirements,
        )
        assessments = self._assess_images(claim_row, claim_understanding)
        aggregated = aggregate_evidence(
            claim=claim_understanding,
            assessments=assessments,
            user_history=self.user_histories.get(claim_row.user_id),
        )

        justification = aggregated.claim_status_justification
        if aggregated.supporting_image_ids:
            justification = f"{justification} Supporting images: {';'.join(aggregated.supporting_image_ids)}."

        output_row = OutputRow(
            user_id=claim_row.user_id,
            image_paths=";".join(claim_row.image_paths),
            user_claim=claim_row.user_claim,
            claim_object=claim_row.claim_object,
            evidence_standard_met=str(aggregated.evidence_standard_met).lower(),
            evidence_standard_met_reason=aggregated.evidence_standard_met_reason,
            risk_flags=";".join(aggregated.risk_flags),
            issue_type=aggregated.issue_type,
            object_part=aggregated.object_part,
            claim_status=aggregated.claim_status,
            claim_status_justification=justification,
            supporting_image_ids=";".join(aggregated.supporting_image_ids) if aggregated.supporting_image_ids else "none",
            valid_image=str(aggregated.valid_image).lower(),
            severity=aggregated.severity,
        )

        debug = {
            "claim_understanding": {
                "summary": claim_understanding.summary,
                "primary_issue_type": claim_understanding.primary_issue_type,
                "primary_object_part": claim_understanding.primary_object_part,
                "severity_hint": claim_understanding.severity_hint,
                "explicit_multi_part_claim": claim_understanding.explicit_multi_part_claim,
                "suspicious_text_present": claim_understanding.suspicious_text_present,
            },
            "image_assessments": [assessment.metadata | {"image_id": assessment.image_id} for assessment in assessments],
            "aggregated": {
                "confidence": aggregated.confidence,
                "observations": aggregated.observations,
            },
        }
        return output_row, debug

    def predict_rows(self, claim_rows: list[ClaimRow]) -> tuple[list[OutputRow], list[dict]]:
        outputs: list[OutputRow] = []
        debug_rows: list[dict] = []
        for claim_row in claim_rows:
            output_row, debug = self.predict_row(claim_row)
            outputs.append(output_row)
            debug_rows.append(debug)
        return outputs, debug_rows
