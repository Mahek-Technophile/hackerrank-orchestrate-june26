from __future__ import annotations

from pathlib import Path


def build_evaluation_report(metrics: dict, strategy_summary: str, operational_notes: list[str], ablations: list[str]) -> str:
    lines = [
        "# Evaluation Report",
        "",
        "## Final Strategy",
        "",
        strategy_summary,
        "",
        "## Metrics",
        "",
    ]
    for key, value in metrics.items():
        if key == "confusion_matrix":
            continue
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Confusion Matrix", ""])
    for key, value in metrics.get("confusion_matrix", {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Operational Analysis", ""])
    for note in operational_notes:
        lines.append(f"- {note}")
    lines.extend(["", "## Ablation Recommendations", ""])
    for note in ablations:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_markdown(content: str, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
