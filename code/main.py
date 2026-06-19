from __future__ import annotations

import argparse
from pathlib import Path

from claim_verifier import AppConfig, ClaimVerificationPipeline
from claim_verifier.io_utils import (
    load_claim_rows,
    load_evidence_requirements,
    load_user_histories,
    write_json,
    write_output_rows,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the multimodal damage-claim verification pipeline.")
    parser.add_argument("--claims", default="/workspace/dataset/claims.csv", help="Path to claims CSV.")
    parser.add_argument("--user-history", default="/workspace/dataset/user_history.csv", help="Path to user history CSV.")
    parser.add_argument(
        "--evidence-requirements",
        default="/workspace/dataset/evidence_requirements.csv",
        help="Path to evidence requirements CSV.",
    )
    parser.add_argument("--output", default="/workspace/output.csv", help="Path for output CSV.")
    parser.add_argument("--debug-json", default="/workspace/code/evaluation/latest_predictions_debug.json")
    parser.add_argument("--provider", default=None, help="Provider name: offline or openai.")
    parser.add_argument("--model", default=None, help="Vision model identifier.")
    parser.add_argument("--max-workers", type=int, default=None)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    overrides = {}
    if args.provider:
        overrides["provider"] = args.provider
    if args.model:
        overrides["model_name"] = args.model
    if args.max_workers:
        overrides["max_workers"] = args.max_workers
    config = AppConfig.from_env(**overrides)

    claims = load_claim_rows(args.claims)
    histories = load_user_histories(args.user_history)
    requirements = load_evidence_requirements(args.evidence_requirements)

    pipeline = ClaimVerificationPipeline(config=config, requirements=requirements, user_histories=histories)
    output_rows, debug_rows = pipeline.predict_rows(claims)

    write_output_rows(output_rows, args.output)
    write_json(debug_rows, args.debug_json)
    print(f"Wrote {len(output_rows)} predictions to {Path(args.output)}")


if __name__ == "__main__":
    main()
