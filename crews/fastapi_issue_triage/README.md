# fastapi_issue_triage

GitHub Issue Triage + Repro Copilot for `tiangolo/fastapi` (resolved by GitHub to `fastapi/fastapi`).

This crew generates human-review-first triage artifacts from GitHub issues:

- `triage.json`
- `repro_checklist.md`
- `draft_maintainer_reply.md`

It does not auto-comment on GitHub in this MVP.

## 1. Prerequisites

Install the following first:

1. Python `>=3.10`
2. `uv` package manager (`https://docs.astral.sh/uv/`)
3. GitHub token (recommended) for stable API limits

## 2. Full Setup (Ordered Commands)

Run these commands in order.

### Windows PowerShell

```powershell
# 1) Go to repository root
cd C:\Users\ASUS\agentforge

# 2) Go to this crew
cd crews\fastapi_issue_triage

# 3) Create venv and install dependencies
uv venv
uv sync

# 4) Create .env from template
Copy-Item .env.example .env

# 5) Edit .env and set your real token
# (example editor command)
notepad .env

# 6) Run one issue smoke test
& "..\..\venv\Scripts\python.exe" -m src.fastapi_issue_triage.main 14680
```

### macOS/Linux

```bash
# 1) Go to repository root
cd ~/agentforge

# 2) Go to this crew
cd crews/fastapi_issue_triage

# 3) Create venv and install dependencies
uv venv
uv sync

# 4) Create .env from template
cp .env.example .env

# 5) Edit .env and set your real token
nano .env

# 6) Run one issue smoke test
../../venv/bin/python -m src.fastapi_issue_triage.main 14680
```

## 3. `.env` File

A complete template is provided at:

- `crews/fastapi_issue_triage/.env.example`

Minimum required for production-like runs:

- `GITHUB_TOKEN=<your_real_token>`

Useful optional settings:

- `FASTAPI_TARGET_REPO=tiangolo/fastapi`
- `FASTAPI_ENABLE_RELATED_SEARCH=0` (recommended to reduce API consumption)
- `FASTAPI_ISSUE_REF=14680` (default issue if CLI arg omitted)

LLM enhancement is optional. Without LLM keys, deterministic triage still works.

## 4. Run Modes

### A) Single issue run

```powershell
cd C:\Users\ASUS\agentforge\crews\fastapi_issue_triage
& "..\..\venv\Scripts\python.exe" -m src.fastapi_issue_triage.main 14680
```

Also supports:

- Issue URL: `https://github.com/fastapi/fastapi/issues/14680`
- `owner/repo#number`: `fastapi/fastapi#14680`

### B) Batch run by explicit list

```powershell
& "..\..\venv\Scripts\python.exe" -m src.fastapi_issue_triage.batch --issue 14680 --issue 14918 --issue 14888
```

### C) Batch run by issue file

Create `issues.txt` (one issue reference per line), then:

```powershell
& "..\..\venv\Scripts\python.exe" -m src.fastapi_issue_triage.batch --issue-file issues.txt --limit 20
```

## 5. Output Locations

### Single issue

Outputs are written to:

- `crews/fastapi_issue_triage/outputs/issue_<number>_<timestamp>/`

Files inside:

- `triage.json`
- `repro_checklist.md`
- `draft_maintainer_reply.md`
- `raw_issue_context.json`

### Batch run

Summary written to:

- `crews/fastapi_issue_triage/outputs/batch_<timestamp>/batch_summary.json`

## 6. Manual Accuracy Workflow (`eval.csv`)

### Step 1: Generate template CSV from a batch summary

```powershell
& "..\..\venv\Scripts\python.exe" -m src.fastapi_issue_triage.eval template --summary outputs\batch_20260214_031453Z\batch_summary.json
```

This creates:

- `outputs\batch_20260214_031453Z\eval_template.csv`

Columns to fill manually:

- `actual_issue_type`
- `actual_severity`
- `actual_component_guess`
- `actual_action`

### Step 2: Score the labeled CSV

```powershell
& "..\..\venv\Scripts\python.exe" -m src.fastapi_issue_triage.eval score --csv outputs\batch_20260214_031453Z\eval_template.csv
```

Optional report export:

```powershell
& "..\..\venv\Scripts\python.exe" -m src.fastapi_issue_triage.eval score --csv outputs\batch_20260214_031453Z\eval_template.csv --output outputs\batch_20260214_031453Z\eval_score.json
```

## 7. Script Aliases (via `uv run`)

```powershell
uv run fastapi_issue_triage 14680
uv run fastapi_issue_triage_batch --issue-file issues.txt --limit 20
uv run fastapi_issue_triage_eval template --summary outputs/batch_20260214_031453Z/batch_summary.json
uv run fastapi_issue_triage_eval score --csv outputs/batch_20260214_031453Z/eval_template.csv
```

## 8. Triage Schema

`triage.json` includes:

- `issue_type`: `bug | support | feature | docs`
- `severity`: `low | medium | high | critical`
- `component_guess`: `routing | dependencies | validation | docs | deployment | other`
- `missing_info`: list of follow-up questions
- `confidence`: float `[0.0, 1.0]`
- `action`: `human_review | ready_to_reply`

Escalation rule:

- If `confidence < 0.65` or `severity == critical`, action is forced to `human_review`.

## 9. Troubleshooting

### `401 Bad credentials`

- Token is invalid, expired, or pasted incorrectly.
- Verify:

```powershell
$h = @{ Authorization = "Bearer $env:GITHUB_TOKEN"; Accept = "application/vnd.github+json"; "User-Agent" = "agentforge" }
(Invoke-RestMethod https://api.github.com/user -Headers $h).login
```

### `403 rate limit exceeded`

- Set a valid `GITHUB_TOKEN` in `.env`.
- Keep `FASTAPI_ENABLE_RELATED_SEARCH=0` for lower API usage.

### `ModuleNotFoundError: crewai`

- Use repo venv python:
- Windows: `..\..\venv\Scripts\python.exe`
- macOS/Linux: `../../venv/bin/python`

### Pull request URL provided

- This crew supports issues only. Use an `/issues/<number>` reference, not `/pull/<number>`.
