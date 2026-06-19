from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .schemas import ClaimRow, EvidenceRequirement, OUTPUT_COLUMNS, OutputRow, UserHistory


def _split_semicolon(value: str) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(";") if item.strip()]


def load_claim_rows(csv_path: str | Path) -> list[ClaimRow]:
    rows: list[ClaimRow] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                ClaimRow(
                    user_id=row["user_id"],
                    image_paths=_split_semicolon(row["image_paths"]),
                    user_claim=row["user_claim"],
                    claim_object=row["claim_object"],
                    raw_row=row,
                )
            )
    return rows


def load_user_histories(csv_path: str | Path) -> dict[str, UserHistory]:
    histories: dict[str, UserHistory] = {}
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            histories[row["user_id"]] = UserHistory(
                user_id=row["user_id"],
                past_claim_count=int(row["past_claim_count"]),
                accept_claim=int(row["accept_claim"]),
                manual_review_claim=int(row["manual_review_claim"]),
                rejected_claim=int(row["rejected_claim"]),
                last_90_days_claim_count=int(row["last_90_days_claim_count"]),
                history_flags=_split_semicolon(row["history_flags"]),
                history_summary=row["history_summary"],
            )
    return histories


def load_evidence_requirements(csv_path: str | Path) -> list[EvidenceRequirement]:
    requirements: list[EvidenceRequirement] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            requirements.append(
                EvidenceRequirement(
                    requirement_id=row["requirement_id"],
                    claim_object=row["claim_object"],
                    applies_to=row["applies_to"],
                    minimum_image_evidence=row["minimum_image_evidence"],
                )
            )
    return requirements


def write_output_rows(rows: Iterable[OutputRow], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(OUTPUT_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_dict())


def write_json(data: object, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
