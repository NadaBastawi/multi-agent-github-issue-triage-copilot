# AgentForge TriageCrew — Multi-Agent GitHub Issue Triage System

This TriageCrew converts GitHub issue text into structured triage output, a reproducibility checklist, and a draft maintainer reply. It is designed to cut issue review time for maintainers by splitting issue handling into four focused agents and keeping the final decision under human review.

## Architecture

- **Issue Intake**: reads the GitHub issue, captures title/body/context, and produces a normalized issue summary.
- **Triage Analyst**: classifies issue type and severity, identifies missing details, and creates structured triage output.
- **Maintainer Response**: drafts a clear, maintainable reply with suggested next steps or follow-up questions.
- **Quality Gate**: keeps the process human-in-the-loop by validating generated artifacts before any maintainer action.

Simple pipeline diagram:

```
[Issue Intake] -> [Triage Analyst] -> [Maintainer Response] -> [Quality Gate]
      |                 |                     |
      v                 v                     v
 triage.json   repro_checklist.md   draft_maintainer_reply.md
```

## Tech Stack

- Python
- CrewAI
- AgentForge
- GitHub API
- uv

## Project Structure

```
.
├── .github/workflows/            # CI definitions for linting, tests, security, and build
├── agentforge/                   # core framework and agent implementation
├── crews/                        # production crews for specific workflows
│   ├── fastapi_issue_triage/     # GitHub issue triage crew for FastAPI issues
│   ├── simple_writer/            # example crew for content generation
│   └── tech_blog_writer_final/   # example crew for technical blog generation
├── LICENSE
├── MANIFEST.in
├── pyproject.toml                # project configuration and uv workspace metadata
└── README.md
```

- `agentforge/` contains the reusable multi-agent logic.
- `crews/` contains crew-specific entry points and settings.
- `.github/workflows/` holds continuous integration for this repository.
- `pyproject.toml` configures packaging and `uv` dependency management.

## Quick Start

### Prerequisites

- Python `>=3.10`
- `uv` installed
- GitHub API token available as `GITHUB_TOKEN`
- `.env.example` is available in `crews/fastapi_issue_triage/`

### Installation

```bash
git clone https://github.com/NadaBastawi/multi-agent-github-issue-triage-copilot
cd multi-agent-github-issue-triage-copilot
python -m pip install --upgrade pip
pip install uv
# or the official one-liner:
curl -Lsf https://astral.sh/uv/install.sh | sh
cd crews/fastapi_issue_triage
uv sync
cp .env.example .env
```

### Environment variables

Edit `crews/fastapi_issue_triage/.env` and set at least:

```bash
GITHUB_TOKEN=<your_github_token>
```

Optional variables supported by the FastAPI crew:

- `FASTAPI_TARGET_REPO=tiangolo/fastapi`
- `FASTAPI_ENABLE_RELATED_SEARCH=0`
- `FASTAPI_ISSUE_REF=<issue_number>`

### Run the FastAPI issue triage crew

```bash
uv run fastapi_issue_triage "https://github.com/tiangolo/fastapi/issues/12176"
```

## Sample Output

The FastAPI triage crew generates three primary artifacts:

- `triage.json`: structured classification of the issue, including type, severity, missing information, confidence, and recommended action.
- `repro_checklist.md`: a reproducibility checklist or verification guide for maintainers and contributors to confirm the issue.
- `draft_maintainer_reply.md`: a polished maintainer response draft that can be reviewed and posted manually.

Example `draft_maintainer_reply.md` content:

```markdown
Hi @tiangolo,

Thanks for reporting this issue. I reviewed the traceback and the current routing logic suggests the failure is related to `response_model` handling in the latest FastAPI release. Can you confirm whether you are using `pydantic>=2.0` and whether the same error occurs with a minimal reproduction that only includes the route definition and response model?

If the issue persists, please share the exact dependency versions and the snippet used to reproduce the failure.

Thanks,
The FastAPI triage team
```

## Design Decisions

- **Multi-agent instead of a single LLM call**: splitting issue intake, classification, response drafting, and validation reduces prompt complexity and makes each stage easier to audit.
- **Role-based crew architecture**: distinct agents for each responsibility make the workflow easier to maintain and tune, and they produce discrete artifacts that can be validated independently.
- **Human-in-the-loop quality gate**: keeps final approval with a maintainer, preventing automated posting of replies and enabling a trusted review step.

## Future Improvements

- Add GitHub Actions integration to run triage automatically on new issues.
- Support repo-specific triage policies for multiple maintainers or project conventions.
- Add a review UI or Slack/Teams notification channel for faster maintainer approval.
