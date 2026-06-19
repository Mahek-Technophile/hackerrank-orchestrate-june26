from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from claim_verifier import AppConfig, ClaimVerificationPipeline
from claim_verifier.io_utils import (
    load_claim_rows,
    load_evidence_requirements,
    load_user_histories,
    write_json,
    write_output_rows,
)
from claim_verifier.metrics import evaluate_predictions
from claim_verifier.reporting import build_evaluation_report, write_markdown


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the damage-claim verification pipeline on sample_claims.csv.")
    parser.add_argument("--sample-claims", default="/workspace/dataset/sample_claims.csv")
    parser.add_argument("--user-history", default="/workspace/dataset/user_history.csv")
    parser.add_argument("--evidence-requirements", default="/workspace/dataset/evidence_requirements.csv")
    parser.add_argument("--predictions", default="/workspace/code/evaluation/sample_predictions.csv")
    parser.add_argument("--report", default="/workspace/code/evaluation/evaluation_report.md")
    parser.add_argument("--metrics-json", default="/workspace/code/evaluation/evaluation_metrics.json")
    parser.add_argument("--provider", default=None)
    parser.add_argument("--model", default=None)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    overrides = {}
    if args.provider:
        overrides["provider"] = args.provider
    if args.model:
        overrides["model_name"] = args.model
    config = AppConfig.from_env(**overrides)

    claims = load_claim_rows(args.sample_claims)
    histories = load_user_histories(args.user_history)
    requirements = load_evidence_requirements(args.evidence_requirements)

    pipeline = ClaimVerificationPipeline(config=config, requirements=requirements, user_histories=histories)
    output_rows, debug_rows = pipeline.predict_rows(claims)
    write_output_rows(output_rows, args.predictions)
    metrics = evaluate_predictions(args.sample_claims, args.predictions)
    write_json(metrics, args.metrics_json)
    write_json(debug_rows, "/workspace/code/evaluation/sample_predictions_debug.json")

    strategy_summary = (
        "The pipeline uses deterministic text parsing, image-level multimodal assessment, "
        "evidence aggregation, and a separate risk layer that never overrides clear visual evidence."
    )
    operational_notes = [
        "OpenAI mode performs one multimodal image call per image and reuses cached responses keyed by image bytes and claim context.",
        "Offline mode remains runnable without API keys but is intentionally conservative and is suitable for smoke tests rather than leaderboard use.",
        "Recommended batch flow: evaluate on sample_claims.csv, review error slices, then run code/main.py on claims.csv.",
        "Approximate cost depends on provider, image count, and prompt size; evaluation_report.md should be updated with the actual chosen model pricing before submission.",
    ]
    ablations = [
        "Compare text-only claim parsing plus VLM image review against a single end-to-end VLM adjudication prompt.",
        "Measure impact of self-consistency by running a second verification pass only on low-confidence rows.",
        "Test a cheaper first-pass model with escalation to a stronger model for rows flagged manual_review_required or not_enough_information.",
    ]
    report = build_evaluation_report(metrics, strategy_summary, operational_notes, ablations)
    write_markdown(report, args.report)
    print(f"Evaluation complete. Report written to {args.report}")


if __name__ == "__main__":
    main()
