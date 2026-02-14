#!/usr/bin/env python3
"""
Evaluation helpers for fastapi_issue_triage.

Commands:
- template: generate a manual labeling CSV from batch_summary.json
- score: compute accuracy metrics from the labeled CSV
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


PRED_FIELDS = {
    "issue_type": "pred_issue_type",
    "severity": "pred_severity",
    "component_guess": "pred_component_guess",
    "action": "pred_action",
}

ACTUAL_FIELDS = {
    "issue_type": "actual_issue_type",
    "severity": "actual_severity",
    "component_guess": "actual_component_guess",
    "action": "actual_action",
}


def _normalize(value: str) -> str:
    """Normalize label values for comparison."""
    return (value or "").strip().lower()


def _read_summary(path: Path) -> Dict:
    """Read batch summary json."""
    return json.loads(path.read_text(encoding="utf-8"))


def _to_eval_rows(summary_data: Dict, include_failed: bool) -> List[Dict[str, str]]:
    """Convert summary JSON results to evaluation rows."""
    rows: List[Dict[str, str]] = []
    for result in summary_data.get("results", []):
        status = result.get("status", "unknown")
        if status != "completed" and not include_failed:
            continue

        triage = result.get("triage", {})
        row = {
            "issue_number": str(result.get("issue_number", "")),
            "issue_reference": str(result.get("issue_reference", "")),
            "issue_url": str(result.get("issue_url", "")),
            "status": status,
            "pred_issue_type": str(triage.get("issue_type", "")),
            "pred_severity": str(triage.get("severity", "")),
            "pred_component_guess": str(triage.get("component_guess", "")),
            "pred_action": str(triage.get("action", "")),
            "pred_confidence": str(triage.get("confidence", "")),
            "pred_missing_info_count": str(len(triage.get("missing_info", []) or [])),
            "actual_issue_type": "",
            "actual_severity": "",
            "actual_component_guess": "",
            "actual_action": "",
            "review_notes": "",
        }
        rows.append(row)
    return rows


def _write_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    """Write rows to CSV."""
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _load_csv_rows(path: Path) -> List[Dict[str, str]]:
    """Load CSV rows."""
    with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
        reader = csv.DictReader(file_obj)
        return list(reader)


def _score_field(rows: List[Dict[str, str]], pred_col: str, actual_col: str) -> Dict[str, float]:
    """Score one predicted field against actual labels."""
    comparable = []
    for row in rows:
        pred = _normalize(row.get(pred_col, ""))
        actual = _normalize(row.get(actual_col, ""))
        if not actual:
            continue
        comparable.append((pred, actual))

    total = len(comparable)
    correct = sum(1 for pred, actual in comparable if pred == actual)
    accuracy = (correct / total) if total else 0.0
    return {"labeled": total, "correct": correct, "accuracy": round(accuracy, 4)}


def _score_overall(rows: List[Dict[str, str]]) -> Dict[str, float]:
    """Score rows where all actual columns are filled."""
    full_rows: List[Tuple[bool, Dict[str, str]]] = []
    for row in rows:
        if not all(_normalize(row.get(col, "")) for col in ACTUAL_FIELDS.values()):
            continue
        is_correct = True
        for key in PRED_FIELDS:
            pred = _normalize(row.get(PRED_FIELDS[key], ""))
            actual = _normalize(row.get(ACTUAL_FIELDS[key], ""))
            if pred != actual:
                is_correct = False
                break
        full_rows.append((is_correct, row))

    total = len(full_rows)
    correct = sum(1 for ok, _ in full_rows if ok)
    accuracy = (correct / total) if total else 0.0
    return {"fully_labeled_rows": total, "all_fields_correct": correct, "accuracy": round(accuracy, 4)}


def _cmd_template(args: argparse.Namespace) -> int:
    summary_path = Path(args.summary)
    if not summary_path.exists():
        print(f"Summary file not found: {summary_path}")
        return 1

    summary_data = _read_summary(summary_path)
    rows = _to_eval_rows(summary_data, include_failed=args.include_failed)
    if not rows:
        print("No rows found to export from summary.")
        return 1

    output_path = Path(args.output) if args.output else summary_path.with_name("eval_template.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output_path, rows)

    print(f"Wrote evaluation template: {output_path}")
    print("Fill `actual_*` columns, then run `score` command.")
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        return 1

    rows = _load_csv_rows(csv_path)
    if not rows:
        print("CSV has no rows.")
        return 1

    summary = {
        "file": str(csv_path),
        "rows": len(rows),
        "issue_type": _score_field(rows, "pred_issue_type", "actual_issue_type"),
        "severity": _score_field(rows, "pred_severity", "actual_severity"),
        "component_guess": _score_field(rows, "pred_component_guess", "actual_component_guess"),
        "action": _score_field(rows, "pred_action", "actual_action"),
        "overall": _score_overall(rows),
    }

    output_json = json.dumps(summary, indent=2)
    print(output_json)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_json + "\n", encoding="utf-8")
        print(f"Saved score report: {output_path}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluation utilities for fastapi_issue_triage")
    subparsers = parser.add_subparsers(dest="command", required=True)

    template_cmd = subparsers.add_parser("template", help="Generate manual labeling CSV")
    template_cmd.add_argument("--summary", required=True, help="Path to batch_summary.json")
    template_cmd.add_argument("--output", help="Output CSV path (default: alongside summary)")
    template_cmd.add_argument(
        "--include-failed",
        action="store_true",
        help="Include failed rows in template (default: completed only).",
    )
    template_cmd.set_defaults(func=_cmd_template)

    score_cmd = subparsers.add_parser("score", help="Score labeled evaluation CSV")
    score_cmd.add_argument("--csv", required=True, help="Path to labeled eval CSV")
    score_cmd.add_argument("--output", help="Optional output JSON path for score report")
    score_cmd.set_defaults(func=_cmd_score)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
