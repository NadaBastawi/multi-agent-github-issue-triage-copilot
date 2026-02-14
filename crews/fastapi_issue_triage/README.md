# fastapi_issue_triage

GitHub Issue Triage + Repro Copilot for FastAPI issues.

This crew generates:

- `triage.json`
- `repro_checklist.md`
- `draft_maintainer_reply.md`

The workflow is human-in-the-loop (no auto-comment posting in this MVP).

## 1) Prerequisites

1. Python `>=3.10`
2. `uv` installed (`https://docs.astral.sh/uv/`)
3. GitHub token (recommended for stable API limits)

## 2) Setup (Ordered Commands)

### Windows PowerShell

```powershell
# 1) Go to your local clone root
cd <path-to-agentforge>

# 2) Go to this crew
cd crews\fastapi_issue_triage

# 3) Create env and install dependencies
uv venv
uv sync

# 4) Create local env file
Copy-Item .env.example .env

# 5) Edit .env and set your real token
notepad .env
```

### macOS/Linux

```bash
# 1) Go to your local clone root
cd <path-to-agentforge>

# 2) Go to this crew
cd crews/fastapi_issue_triage

# 3) Create env and install dependencies
uv venv
uv sync

# 4) Create local env file
cp .env.example .env

# 5) Edit .env and set your real token
nano .env
```

## 3) Environment Variables

Template file:

- `crews/fastapi_issue_triage/.env.example`

Minimum:

- `GITHUB_TOKEN=<your_real_token>`

Useful optional:

- `FASTAPI_TARGET_REPO=tiangolo/fastapi`
- `FASTAPI_ENABLE_RELATED_SEARCH=0`
- `FASTAPI_ISSUE_REF=14680`

LLM enhancement is optional. Deterministic mode works without LLM keys.

## 4) Run Commands

Run from `crews/fastapi_issue_triage`.

### A) Single issue

```powershell
uv run fastapi_issue_triage 14680
```

Also accepted:

- `https://github.com/fastapi/fastapi/issues/14680`
- `fastapi/fastapi#14680`

### B) Batch from explicit issue list

```powershell
uv run fastapi_issue_triage_batch --issue 14680 --issue 14918 --issue 14888
```

### C) Batch from file

Create `issues.txt` (one issue reference per line), then:

```powershell
uv run fastapi_issue_triage_batch --issue-file issues.txt --limit 20
```

### D) Legacy module form (equivalent)

```powershell
uv run python -m fastapi_issue_triage.main 14680
uv run python -m fastapi_issue_triage.batch --issue-file issues.txt --limit 20
```

## 5) Output Locations

### Single issue output

- `crews/fastapi_issue_triage/outputs/issue_<number>_<timestamp>/`

Contains:

- `triage.json`
- `repro_checklist.md`
- `draft_maintainer_reply.md`
- `raw_issue_context.json`

### Batch output

- `crews/fastapi_issue_triage/outputs/batch_<timestamp>/batch_summary.json`

## 6) Manual Accuracy Workflow (`eval.csv`)

### Step 1: Generate labeling template

```powershell
uv run fastapi_issue_triage_eval template --summary outputs/batch_20260214_031453Z/batch_summary.json
```

This creates:

- `outputs/batch_20260214_031453Z/eval_template.csv`

Fill these columns:

- `actual_issue_type`
- `actual_severity`
- `actual_component_guess`
- `actual_action`

### Step 2: Score labels

```powershell
uv run fastapi_issue_triage_eval score --csv outputs/batch_20260214_031453Z/eval_template.csv
```

Optional report output:

```powershell
uv run fastapi_issue_triage_eval score --csv outputs/batch_20260214_031453Z/eval_template.csv --output outputs/batch_20260214_031453Z/eval_score.json
```

## 7) Triage Schema

`triage.json` fields:

- `issue_type`: `bug | support | feature | docs`
- `severity`: `low | medium | high | critical`
- `component_guess`: `routing | dependencies | validation | docs | deployment | other`
- `missing_info`: follow-up question list
- `confidence`: float `[0.0, 1.0]`
- `action`: `human_review | ready_to_reply`

Escalation rule:

- Force `human_review` if `confidence < 0.65` or `severity == critical`.

## 8) Troubleshooting

### 401 Bad credentials

Verify your token:

```powershell
$h = @{ Authorization = "Bearer $env:GITHUB_TOKEN"; Accept = "application/vnd.github+json"; "User-Agent" = "agentforge" }
(Invoke-RestMethod https://api.github.com/user -Headers $h).login
```

### 403 Rate limit exceeded

- Ensure valid `GITHUB_TOKEN` in `.env`
- Keep `FASTAPI_ENABLE_RELATED_SEARCH=0`

### Pull request URL provided

- This crew supports `/issues/<number>` only, not `/pull/<number>`.
