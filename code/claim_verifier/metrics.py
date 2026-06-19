from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def _f1(tp: int, fp: int, fn: int) -> float:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return (2 * precision * recall / (precision + recall)) if precision + recall else 0.0


def evaluate_predictions(expected_csv: str | Path, predicted_csv: str | Path) -> dict:
    with Path(expected_csv).open("r", encoding="utf-8", newline="") as handle:
        expected_rows = list(csv.DictReader(handle))
    with Path(predicted_csv).open("r", encoding="utf-8", newline="") as handle:
        predicted_rows = list(csv.DictReader(handle))

    if len(expected_rows) != len(predicted_rows):
        raise ValueError("Expected and predicted row counts differ.")

    total = len(expected_rows)
    exact_match = 0
    claim_status_correct = 0
    evidence_correct = 0
    severity_correct = 0
    issue_correct = 0
    part_correct = 0
    confusion: Counter[tuple[str, str]] = Counter()

    labels = ["supported", "contradicted", "not_enough_information"]
    per_label = {label: {"tp": 0, "fp": 0, "fn": 0} for label in labels}
    grounding_hits = 0

    for expected, predicted in zip(expected_rows, predicted_rows):
        keys = ("claim_status", "issue_type", "object_part", "severity", "evidence_standard_met")
        if all(expected[key] == predicted[key] for key in keys):
            exact_match += 1
        if expected["claim_status"] == predicted["claim_status"]:
            claim_status_correct += 1
        if expected["evidence_standard_met"] == predicted["evidence_standard_met"]:
            evidence_correct += 1
        if expected["severity"] == predicted["severity"]:
            severity_correct += 1
        if expected["issue_type"] == predicted["issue_type"]:
            issue_correct += 1
        if expected["object_part"] == predicted["object_part"]:
            part_correct += 1
        confusion[(expected["claim_status"], predicted["claim_status"])] += 1

        for label in labels:
            if expected["claim_status"] == label and predicted["claim_status"] == label:
                per_label[label]["tp"] += 1
            elif expected["claim_status"] != label and predicted["claim_status"] == label:
                per_label[label]["fp"] += 1
            elif expected["claim_status"] == label and predicted["claim_status"] != label:
                per_label[label]["fn"] += 1

        expected_support = set(filter(None, expected["supporting_image_ids"].split(";"))) - {"none"}
        predicted_support = set(filter(None, predicted["supporting_image_ids"].split(";"))) - {"none"}
        if not expected_support and not predicted_support:
            grounding_hits += 1
        elif expected_support.intersection(predicted_support):
            grounding_hits += 1

    macro_f1 = sum(_f1(**per_label[label]) for label in labels) / len(labels)
    return {
        "row_count": total,
        "exact_match_rate": round(exact_match / total, 4),
        "claim_status_accuracy": round(claim_status_correct / total, 4),
        "evidence_standard_accuracy": round(evidence_correct / total, 4),
        "issue_type_accuracy": round(issue_correct / total, 4),
        "object_part_accuracy": round(part_correct / total, 4),
        "severity_accuracy": round(severity_correct / total, 4),
        "grounding_overlap_rate": round(grounding_hits / total, 4),
        "macro_f1_claim_status": round(macro_f1, 4),
        "confusion_matrix": {f"{k[0]}->{k[1]}": v for k, v in sorted(confusion.items())},
    }
