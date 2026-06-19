# Evaluation Report

## Final Strategy

The pipeline uses deterministic text parsing, image-level multimodal assessment, evidence aggregation, and a separate risk layer that never overrides clear visual evidence.

## Metrics

- row_count: 20
- exact_match_rate: 0.05
- claim_status_accuracy: 0.1
- evidence_standard_accuracy: 0.1
- issue_type_accuracy: 0.15
- object_part_accuracy: 0.65
- severity_accuracy: 0.1
- grounding_overlap_rate: 0.1
- macro_f1_claim_status: 0.0606

## Confusion Matrix

- contradicted->not_enough_information: 5
- not_enough_information->not_enough_information: 2
- supported->not_enough_information: 13

## Operational Analysis

- OpenAI mode performs one multimodal image call per image and reuses cached responses keyed by image bytes and claim context.
- Offline mode remains runnable without API keys but is intentionally conservative and is suitable for smoke tests rather than leaderboard use.
- Recommended batch flow: evaluate on sample_claims.csv, review error slices, then run code/main.py on claims.csv.
- Approximate cost depends on provider, image count, and prompt size; evaluation_report.md should be updated with the actual chosen model pricing before submission.

## Ablation Recommendations

- Compare text-only claim parsing plus VLM image review against a single end-to-end VLM adjudication prompt.
- Measure impact of self-consistency by running a second verification pass only on low-confidence rows.
- Test a cheaper first-pass model with escalation to a stronger model for rows flagged manual_review_required or not_enough_information.
