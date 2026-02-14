#!/usr/bin/env python3
"""
fastapi_issue_triage - CrewAI project

GitHub issue triage and maintainer reply copilot for tiangolo/fastapi.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .crew import FastapiIssueTriageCrew


def _load_project_env() -> None:
    """Load .env file from crew root if present."""
    project_root = Path(__file__).resolve().parents[2]
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file, override=False)


def main():
    """Main entry point for the crew."""
    _load_project_env()

    if len(sys.argv) > 1:
        task_input = " ".join(sys.argv[1:]).strip()
        print(f"[INFO] Task input: {task_input}")
    else:
        task_input = os.getenv("FASTAPI_ISSUE_REF", "").strip()
        if task_input:
            print(f"[INFO] Using FASTAPI_ISSUE_REF={task_input}")
        else:
            print("[ERROR] Missing issue reference.")
            print("Usage: python -m src.fastapi_issue_triage.main <issue_number_or_url>")
            print("Example: python -m src.fastapi_issue_triage.main https://github.com/tiangolo/fastapi/issues/12176")
            return 1

    print("[INFO] Initializing FastapiIssueTriageCrew...")
    crew = FastapiIssueTriageCrew()
    result = crew.run(task_input)

    print("\n" + "=" * 72)
    print("FASTAPI ISSUE TRIAGE COMPLETED")
    print("=" * 72)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
