#!/usr/bin/env python3
"""
Batch runner for fastapi_issue_triage.

Use this to process a list of historical issues for quick MVP evaluation.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from .crew import FastapiIssueTriageCrew


def _load_project_env() -> None:
    """Load .env file from crew root if present."""
    project_root = Path(__file__).resolve().parents[2]
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)


def _load_issue_refs_from_file(file_path: str) -> List[str]:
    """Load issue references from text file (one per line)."""
    refs: List[str] = []
    for line in Path(file_path).read_text(encoding="utf-8").splitlines():
        value = line.strip().lstrip("\ufeff")
        if not value or value.startswith("#"):
            continue
        refs.append(value)
    return refs


def main() -> int:
    """CLI entry point for batch execution."""
    _load_project_env()

    parser = argparse.ArgumentParser(description="Batch triage FastAPI issues")
    parser.add_argument(
        "--issue",
        action="append",
        help="Issue reference (number, URL, or owner/repo#number). Repeat for multiple.",
    )
    parser.add_argument(
        "--issue-file",
        help="Path to text file with one issue reference per line.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit after loading all issue refs.",
    )
    args = parser.parse_args()

    issue_refs: List[str] = []
    if args.issue:
        issue_refs.extend(args.issue)
    if args.issue_file:
        issue_refs.extend(_load_issue_refs_from_file(args.issue_file))

    deduped_refs = []
    seen = set()
    for ref in issue_refs:
        key = ref.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped_refs.append(key)
    issue_refs = deduped_refs

    if args.limit and args.limit > 0:
        issue_refs = issue_refs[: args.limit]

    if not issue_refs:
        print("No issue references provided. Use --issue or --issue-file.")
        return 1

    crew = FastapiIssueTriageCrew()
    results = []
    success_count = 0

    for index, issue_ref in enumerate(issue_refs, start=1):
        print(f"[{index}/{len(issue_refs)}] Processing {issue_ref}...")
        result_raw = crew.run(issue_ref)
        try:
            result = json.loads(result_raw)
        except json.JSONDecodeError:
            result = {"status": "failed", "error": "non-json result", "raw": result_raw}
        results.append(result)
        if result.get("status") == "completed":
            success_count += 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    batch_output_dir = Path("outputs") / f"batch_{timestamp}"
    batch_output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_issues": len(issue_refs),
        "successful_runs": success_count,
        "failed_runs": len(issue_refs) - success_count,
        "results": results,
    }

    summary_path = batch_output_dir / "batch_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Batch completed. Summary written to: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
