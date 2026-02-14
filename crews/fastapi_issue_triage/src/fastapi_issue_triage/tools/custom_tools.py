"""
Custom tools for fastapi_issue_triage crew.

This module provides:
1. GitHub issue ingestion for tiangolo/fastapi
2. Deterministic triage heuristics
3. Repro checklist and maintainer reply drafting helpers
4. CrewAI tool wrappers
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, parse, request

from crewai.tools import BaseTool

DEFAULT_REPO = "tiangolo/fastapi"
TRIAGE_TYPES = {"bug", "support", "feature", "docs"}
SEVERITY_LEVELS = {"low", "medium", "high", "critical"}
COMPONENTS = {"routing", "dependencies", "validation", "docs", "deployment", "other"}
ACTIONS = {"human_review", "ready_to_reply"}


def _truncate(text_value: str, max_chars: int = 1600) -> str:
    """Truncate long strings while preserving readability."""
    if len(text_value) <= max_chars:
        return text_value
    return f"{text_value[:max_chars].rstrip()}\n...[truncated]"


def _normalize_space(text_value: str) -> str:
    """Normalize whitespace for easier keyword matching."""
    return re.sub(r"\s+", " ", text_value or "").strip()


def _safe_json_loads(raw: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Safely parse JSON content."""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except (TypeError, json.JSONDecodeError):
        pass
    return default or {}


def parse_issue_reference(issue_reference: str, default_repo: str = DEFAULT_REPO) -> Tuple[str, int]:
    """
    Parse a GitHub issue reference into (repo, issue_number).

    Accepted formats:
    - https://github.com/owner/repo/issues/123
    - owner/repo#123
    - owner/repo/issues/123
    - 123 (uses default_repo)
    - #123 (uses default_repo)
    """
    reference = (issue_reference or "").strip()
    if not reference:
        raise ValueError("Issue reference is empty")

    url_match = re.search(
        r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)",
        reference,
    )
    if url_match:
        return url_match.group(1), int(url_match.group(2))

    hash_match = re.match(
        r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#(\d+)$",
        reference,
    )
    if hash_match:
        return hash_match.group(1), int(hash_match.group(2))

    slash_match = re.match(
        r"^([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/(\d+)$",
        reference,
    )
    if slash_match:
        return slash_match.group(1), int(slash_match.group(2))

    number_match = re.match(r"^#?(\d+)$", reference)
    if number_match:
        return default_repo, int(number_match.group(1))

    raise ValueError(
        "Unsupported issue reference format. Use URL, owner/repo#number, or number."
    )


def _github_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Build GitHub API headers."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agentforge-fastapi-issue-triage",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_get_json(url: str, token: Optional[str] = None) -> Any:
    """GET JSON from GitHub API with basic error normalization."""
    req = request.Request(url, headers=_github_headers(token))
    try:
        with request.urlopen(req, timeout=25) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        trimmed = _truncate(details, 300)
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {trimmed}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Network error while calling GitHub API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("GitHub API returned non-JSON payload") from exc


def _extract_keywords_for_related_search(title: str) -> str:
    """Extract a compact keyword query for related issue search."""
    stop_words = {
        "fastapi",
        "issue",
        "with",
        "from",
        "this",
        "that",
        "when",
        "then",
        "into",
        "using",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]+", title or "")
    filtered = []
    for word in words:
        normalized = word.lower()
        if len(normalized) < 4:
            continue
        if normalized in stop_words:
            continue
        filtered.append(normalized)
    return " ".join(filtered[:4])


def search_related_issues(
    repo: str, issue_number: int, title: str, token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search for a few related issues by title keywords."""
    keywords = _extract_keywords_for_related_search(title)
    if not keywords:
        return []

    query = f"repo:{repo} is:issue {keywords}"
    url = f"https://api.github.com/search/issues?q={parse.quote(query)}&per_page=5"
    payload = _github_get_json(url, token=token)
    items = payload.get("items", []) if isinstance(payload, dict) else []

    related = []
    for item in items:
        number = item.get("number")
        if number == issue_number:
            continue
        related.append(
            {
                "number": number,
                "title": item.get("title", ""),
                "state": item.get("state", ""),
                "url": item.get("html_url", ""),
            }
        )
    return related[:5]


def fetch_issue_snapshot(
    issue_reference: str,
    repo_override: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch a GitHub issue snapshot with comments and related issue references.
    """
    repo, issue_number = parse_issue_reference(
        issue_reference=issue_reference,
        default_repo=repo_override or os.getenv("FASTAPI_TARGET_REPO", DEFAULT_REPO),
    )
    token_value = token or os.getenv("GITHUB_TOKEN")

    issue_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    issue_data = _github_get_json(issue_url, token=token_value)
    if "pull_request" in issue_data:
        raise ValueError("Provided reference points to a pull request, not an issue")

    repository_url = issue_data.get("repository_url", "")
    repo_match = re.search(r"/repos/([^/]+/[^/]+)$", repository_url)
    canonical_repo = repo_match.group(1) if repo_match else repo

    comments_url = f"{issue_url}/comments?per_page=5"
    comments_payload = _github_get_json(comments_url, token=token_value)
    comments_payload = comments_payload if isinstance(comments_payload, list) else []

    recent_comments = []
    for comment in comments_payload:
        recent_comments.append(
            {
                "user": (comment.get("user") or {}).get("login", ""),
                "created_at": comment.get("created_at", ""),
                "body": _truncate(comment.get("body") or "", 800),
            }
        )

    related_issues: List[Dict[str, Any]] = []
    enable_related_search = os.getenv("FASTAPI_ENABLE_RELATED_SEARCH", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if enable_related_search:
        try:
            related_issues = search_related_issues(
                repo=canonical_repo,
                issue_number=issue_number,
                title=issue_data.get("title", ""),
                token=token_value,
            )
        except Exception:
            related_issues = []

    labels = [label.get("name", "") for label in issue_data.get("labels", [])]
    body = issue_data.get("body") or ""

    return {
        "repository": canonical_repo,
        "issue_number": issue_number,
        "issue_url": issue_data.get("html_url", issue_url),
        "title": issue_data.get("title", ""),
        "body": _truncate(body, 14000),
        "state": issue_data.get("state", ""),
        "author": (issue_data.get("user") or {}).get("login", ""),
        "created_at": issue_data.get("created_at", ""),
        "updated_at": issue_data.get("updated_at", ""),
        "labels": labels,
        "comment_count": issue_data.get("comments", 0),
        "recent_comments": recent_comments,
        "related_issues": related_issues,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _aggregate_issue_text(issue_data: Dict[str, Any]) -> str:
    """Aggregate textual issue context for classification."""
    label_text = " ".join(issue_data.get("labels", []))
    comment_text = " ".join(
        [comment.get("body", "") for comment in issue_data.get("recent_comments", [])]
    )
    combined = " ".join(
        [
            issue_data.get("title", ""),
            issue_data.get("body", ""),
            label_text,
            comment_text,
        ]
    )
    return _normalize_space(combined).lower()


def _score_phrase_hits(text_value: str, weighted_phrases: List[Tuple[str, float]]) -> float:
    """Score text using phrase hits with configurable weights."""
    score = 0.0
    for phrase, weight in weighted_phrases:
        if phrase in text_value:
            score += weight
    return score


def _determine_issue_type(title: str, body: str, labels: List[str]) -> str:
    """
    Determine issue type using weighted signals.

    This avoids over-biasing toward feature/docs by preferring:
    bug -> support -> feature -> docs when confidence ties.
    """
    title_text = _normalize_space(title).lower()
    body_text = _normalize_space(body).lower()
    full_text = f"{title_text} {body_text}"
    labels_lower = [label.lower() for label in labels]

    scores = {"bug": 0.0, "support": 0.0, "feature": 0.0, "docs": 0.0}

    # Label signals are strong, but not absolute.
    for label in labels_lower:
        if "bug" in label:
            scores["bug"] += 4.0
        if "question" in label or "support" in label or "usage" in label:
            scores["support"] += 4.0
        if "feature" in label or "enhancement" in label or "proposal" in label:
            scores["feature"] += 4.0
        if "doc" in label or "readme" in label:
            scores["docs"] += 4.0

    bug_phrases_title = [
        ("bug", 2.5),
        ("error", 2.5),
        ("exception", 2.8),
        ("traceback", 3.0),
        ("crash", 3.0),
        ("regression", 2.5),
        ("fails", 2.0),
        ("not working", 2.5),
        ("500", 2.0),
        ("422", 1.8),
    ]
    support_phrases_title = [
        ("question", 2.8),
        ("how to", 3.0),
        ("how can", 2.8),
        ("can i", 2.4),
        ("is it possible", 2.2),
        ("help", 2.2),
        ("clarification", 2.2),
        ("usage", 2.0),
    ]
    feature_phrases_title = [
        ("feature request", 3.2),
        ("enhancement", 2.8),
        ("proposal", 2.4),
        ("please add", 2.6),
        ("add support", 2.6),
        ("support for", 2.0),
        ("would like", 2.0),
    ]
    docs_phrases_title = [
        ("docs", 2.8),
        ("documentation", 3.0),
        ("readme", 2.8),
        ("typo", 3.0),
        ("doc example", 3.2),
        ("tutorial", 2.0),
    ]

    bug_phrases_body = [
        ("traceback", 2.2),
        ("exception", 2.0),
        ("actual behavior", 1.6),
        ("expected behavior", 1.2),
        ("steps to reproduce", 1.8),
        ("fails", 1.6),
        ("error", 1.6),
    ]
    support_phrases_body = [
        ("how to", 1.8),
        ("is there a way", 1.8),
        ("guidance", 1.4),
        ("i am trying to", 1.4),
        ("what is the best way", 1.6),
    ]
    feature_phrases_body = [
        ("feature request", 2.2),
        ("would be nice", 1.8),
        ("it would be great", 1.8),
        ("proposal", 1.4),
        ("new feature", 1.8),
        ("enhancement", 1.6),
    ]
    docs_phrases_body = [
        ("documentation page", 2.2),
        ("docs page", 2.2),
        ("readme", 1.8),
        ("typo", 2.0),
        ("example in docs", 2.2),
        ("incorrect example", 2.0),
    ]

    scores["bug"] += _score_phrase_hits(title_text, bug_phrases_title)
    scores["support"] += _score_phrase_hits(title_text, support_phrases_title)
    scores["feature"] += _score_phrase_hits(title_text, feature_phrases_title)
    scores["docs"] += _score_phrase_hits(title_text, docs_phrases_title)

    scores["bug"] += _score_phrase_hits(full_text, bug_phrases_body)
    scores["support"] += _score_phrase_hits(full_text, support_phrases_body)
    scores["feature"] += _score_phrase_hits(full_text, feature_phrases_body)
    scores["docs"] += _score_phrase_hits(full_text, docs_phrases_body)

    # Title question marks usually indicate support unless bug signals are explicit.
    if "?" in title_text and scores["bug"] < 3.5:
        scores["support"] += 1.8

    # If bug signals are strong, down-weight feature/docs.
    if scores["bug"] >= 4.0:
        scores["feature"] -= 1.0
        scores["docs"] -= 1.0

    # Small normalization floor.
    for key in scores:
        scores[key] = max(scores[key], 0.0)

    max_score = max(scores.values())
    candidates = [kind for kind, score in scores.items() if score == max_score]
    for preferred in ["bug", "support", "feature", "docs"]:
        if preferred in candidates:
            return preferred

    return "support"


def _determine_component(text_blob: str, issue_type: str) -> str:
    """Guess probable FastAPI component based on lexical signals."""
    keyword_map = {
        "routing": {
            "apirouter",
            "include_router",
            "@app.get",
            "@app.post",
            "@router.get",
            "@router.post",
            "path operation",
            "route decorator",
            "url_path_for",
        },
        "dependencies": {
            "dependency",
            "depends(",
            "inject",
            "lifespan",
            "startup event",
            "shutdown event",
            "middleware",
            "starlette",
            "uvicorn",
        },
        "validation": {
            "validationerror",
            "validation error",
            "pydantic",
            "schema",
            "field required",
            "422",
            "response_model",
            "model_config",
        },
        "docs": {
            "docs page",
            "documentation page",
            "openapi docs",
            "swagger ui",
            "redoc ui",
            "doc example",
            "readme",
            "example in docs",
            "incorrect example",
            "typo",
        },
        "deployment": {
            "docker",
            "gunicorn",
            "kubernetes",
            "k8s",
            "nginx",
            "reverse proxy",
            "deployment",
            "production",
        },
    }

    scores = {}
    for component, words in keyword_map.items():
        score = sum(1 for word in words if word in text_blob)
        if score > 0:
            scores[component] = score

    if scores:
        return max(scores, key=scores.get)
    if issue_type == "docs":
        return "docs"
    return "other"


def _determine_severity(issue_type: str, text_blob: str) -> str:
    """Estimate severity from textual indicators."""
    critical_terms = {
        "security vulnerability",
        "remote code execution",
        "arbitrary code execution",
        "privilege escalation",
        "authentication bypass",
        "cve-",
        "data loss",
        "production down",
        "service outage",
        "denial of service",
    }
    high_terms = {
        "crash",
        "cannot start",
        "500",
        "regression",
        "service unavailable",
        "blocking",
        "blocker",
        "outage",
        "unusable",
    }
    medium_terms = {
        "error",
        "exception",
        "fails",
        "failed",
        "not working",
        "broken",
        "incorrect",
        "unexpected",
        "timeout",
        "422",
    }

    if any(term in text_blob for term in critical_terms):
        return "critical"
    if any(term in text_blob for term in high_terms):
        return "high"
    if issue_type == "bug":
        return "medium"
    if issue_type == "support":
        return "medium" if any(term in text_blob for term in medium_terms) else "low"
    if issue_type == "feature":
        feature_urgency = {"blocking", "urgent", "production", "must have"}
        return "medium" if any(term in text_blob for term in feature_urgency) else "low"
    return "low"


def _collect_missing_info(issue_type: str, text_blob: str) -> List[str]:
    """Collect specific missing information questions."""
    questions = []

    has_code_block = "```" in text_blob
    has_traceback = any(
        marker in text_blob for marker in ["traceback", "stack trace", "exception", "error:"]
    )
    has_python_version = bool(re.search(r"python\s*3\.\d+", text_blob))
    has_fastapi_version = bool(
        re.search(r"fastapi\s*(==|>=|<=)?\s*\d+\.\d+(\.\d+)?", text_blob)
        or re.search(r"fastapi version[:\s]+\d+\.\d+(\.\d+)?", text_blob)
    )
    has_repro_steps = any(
        phrase in text_blob
        for phrase in [
            "steps to reproduce",
            "reproduce",
            "expected behavior",
            "actual behavior",
        ]
    )
    has_environment = any(
        token in text_blob for token in ["windows", "linux", "mac", "docker", "kubernetes"]
    )
    has_url = "http://" in text_blob or "https://" in text_blob

    if issue_type == "docs":
        if not has_url:
            questions.append("Please provide the exact documentation page URL.")
        if "expected" not in text_blob or "actual" not in text_blob:
            questions.append("Please clarify the current wording and your expected wording.")
        return questions

    if issue_type == "feature":
        if "use case" not in text_blob and "problem" not in text_blob:
            questions.append("Please describe the concrete use case and why current behavior is insufficient.")
        if "proposed" not in text_blob and "proposal" not in text_blob:
            questions.append("Please include a proposed API or behavior change.")
        if not has_code_block:
            questions.append("If possible, include a short example showing desired behavior.")
        return questions

    if not has_code_block:
        questions.append(
            "Please share a minimal reproducible FastAPI app (single file if possible)."
        )
    if not has_fastapi_version:
        questions.append("Please include your FastAPI, Starlette, and Pydantic versions.")
    if not has_python_version:
        questions.append("Please include your Python version.")
    if not has_environment:
        questions.append("Please include OS/runtime details (local, Docker, cloud, etc.).")
    if issue_type == "bug" and not has_traceback:
        questions.append("Please include the full traceback or exact error output.")
    if issue_type == "bug" and not has_repro_steps:
        questions.append("Please list exact steps to reproduce, expected result, and actual result.")

    return questions


def _calculate_confidence(
    text_blob: str, labels: List[str], missing_info: List[str], issue_type: str
) -> float:
    """Calculate confidence score from issue completeness signals."""
    score = 0.45
    if labels:
        score += 0.08
    if len(text_blob) > 350:
        score += 0.08
    if "```" in text_blob:
        score += 0.1
    if "traceback" in text_blob or "exception" in text_blob:
        score += 0.08
    if re.search(r"python\s*3\.\d+", text_blob):
        score += 0.06
    if re.search(r"fastapi\s*(==|>=|<=)?\s*\d+\.\d+(\.\d+)?", text_blob):
        score += 0.06

    if issue_type in {"docs", "feature"} and len(text_blob) > 120:
        score += 0.05

    penalty = 0.05 if issue_type == "bug" else 0.04 if issue_type == "support" else 0.03
    score -= min(len(missing_info), 4) * penalty
    score = max(0.0, min(score, 0.98))
    return round(score, 2)


def validate_triage_schema(triage: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and validate triage output schema."""
    normalized = dict(triage)
    normalized["issue_type"] = str(normalized.get("issue_type", "bug")).lower()
    normalized["severity"] = str(normalized.get("severity", "medium")).lower()
    normalized["component_guess"] = str(normalized.get("component_guess", "other")).lower()
    normalized["action"] = str(normalized.get("action", "human_review")).lower()

    if normalized["issue_type"] not in TRIAGE_TYPES:
        normalized["issue_type"] = "bug"
    if normalized["severity"] not in SEVERITY_LEVELS:
        normalized["severity"] = "medium"
    if normalized["component_guess"] not in COMPONENTS:
        normalized["component_guess"] = "other"
    if normalized["action"] not in ACTIONS:
        normalized["action"] = "human_review"

    confidence = normalized.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(confidence, 1.0))
    normalized["confidence"] = round(confidence, 2)

    missing = normalized.get("missing_info", [])
    if not isinstance(missing, list):
        missing = [str(missing)]
    normalized["missing_info"] = [str(item).strip() for item in missing if str(item).strip()]

    rationale = normalized.get("rationale", "")
    normalized["rationale"] = str(rationale).strip()

    if normalized["severity"] == "critical" or normalized["confidence"] < 0.65:
        normalized["action"] = "human_review"

    return normalized


def build_baseline_triage(issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build deterministic baseline triage decision."""
    title = issue_data.get("title", "")
    body = issue_data.get("body", "")
    text_blob = _aggregate_issue_text(issue_data)
    labels = issue_data.get("labels", [])
    issue_type = _determine_issue_type(title=title, body=body, labels=labels)
    severity = _determine_severity(issue_type=issue_type, text_blob=text_blob)
    component_guess = _determine_component(text_blob=text_blob, issue_type=issue_type)
    missing_info = _collect_missing_info(issue_type=issue_type, text_blob=text_blob)
    confidence = _calculate_confidence(
        text_blob=text_blob,
        labels=labels,
        missing_info=missing_info,
        issue_type=issue_type,
    )
    action = "human_review" if severity == "critical" or confidence < 0.65 else "ready_to_reply"

    rationale = []
    rationale.append(f"Classified as `{issue_type}` based on title/body and labels.")
    rationale.append(f"Estimated severity `{severity}` from reported impact signals.")
    rationale.append(f"Component guess `{component_guess}` based on keyword overlap.")
    if missing_info:
        rationale.append(f"Detected {len(missing_info)} missing reproducibility details.")

    return validate_triage_schema(
        {
            "issue_type": issue_type,
            "severity": severity,
            "component_guess": component_guess,
            "missing_info": missing_info,
            "confidence": confidence,
            "action": action,
            "rationale": " ".join(rationale),
        }
    )


def build_repro_checklist(issue_data: Dict[str, Any], triage: Dict[str, Any]) -> str:
    """Generate reproducibility checklist markdown."""
    component = triage.get("component_guess", "other")
    missing_info = triage.get("missing_info", [])

    lines = [
        f"# Repro Checklist for FastAPI Issue #{issue_data.get('issue_number')}",
        "",
        "Please check the items below before maintainer deep triage:",
        "",
        "- [ ] Provide a minimal runnable FastAPI example (single file preferred).",
        "- [ ] Include exact steps to reproduce from a clean environment.",
        "- [ ] Include expected behavior and actual behavior.",
        "- [ ] Include Python, FastAPI, Starlette, and Pydantic versions.",
        "- [ ] Include runtime environment details (OS, Docker/cloud, server setup).",
    ]

    component_specific = {
        "routing": "- [ ] Include route decorators, path params, and router mounting setup.",
        "dependencies": "- [ ] Include dependency function signatures and dependency injection chain.",
        "validation": "- [ ] Include request/response models and example payloads triggering failure.",
        "docs": "- [ ] Include page/section URL and expected docs behavior.",
        "deployment": "- [ ] Include app server command, workers, and reverse proxy settings.",
    }
    if component in component_specific:
        lines.append(component_specific[component])

    if missing_info:
        lines.extend(["", "Missing info detected in current report:"])
        for item in missing_info:
            lines.append(f"- [ ] {item}")

    return "\n".join(lines).strip() + "\n"


def build_draft_reply(issue_data: Dict[str, Any], triage: Dict[str, Any]) -> str:
    """Generate draft maintainer reply markdown."""
    issue_number = issue_data.get("issue_number")
    issue_type = triage.get("issue_type", "bug")
    severity = triage.get("severity", "medium")
    component = triage.get("component_guess", "other")
    confidence = triage.get("confidence", 0.0)
    action = triage.get("action", "human_review")
    missing_info = triage.get("missing_info", [])

    lines = [
        f"Thanks for opening this issue and for helping improve FastAPI.",
        "",
        f"Initial triage summary: `{issue_type}` | severity `{severity}` | probable area `{component}`.",
        f"Current triage confidence: `{confidence}`.",
    ]

    if missing_info:
        lines.extend(["", "To move this forward quickly, please share:"])
        for item in missing_info:
            lines.append(f"- {item}")

    if action == "human_review":
        lines.extend(
            [
                "",
                "I am marking this for human maintainer review after the requested details are provided.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Once the requested details are provided, this can likely move directly into maintainer response flow.",
            ]
        )

    lines.extend(
        [
            "",
            f"Issue reference: #{issue_number}",
        ]
    )

    return "\n".join(lines).strip() + "\n"


def extract_json_from_text(text_value: str, required_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Extract first JSON object from markdown/plain text."""
    text_value = text_value or ""

    fence_match = re.search(r"```json\s*(\{.*\})\s*```", text_value, re.IGNORECASE | re.DOTALL)
    candidates = []
    if fence_match:
        candidates.append(fence_match.group(1))

    brace_start = text_value.find("{")
    brace_end = text_value.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        candidates.append(text_value[brace_start : brace_end + 1])

    for candidate in candidates:
        parsed = _safe_json_loads(candidate, default={})
        if not parsed:
            continue
        if required_keys and not all(key in parsed for key in required_keys):
            continue
        return parsed

    return {}


def extract_markdown_section(text_value: str, section_name: str) -> str:
    """Extract markdown section content by a heading marker."""
    pattern = rf"###\s*{re.escape(section_name)}\s*\n(.*?)(?=\n###\s*[A-Z_]+|\Z)"
    match = re.search(pattern, text_value or "", re.DOTALL | re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip()


class GitHubIssueFetcherTool(BaseTool):
    """CrewAI tool: fetch GitHub issue snapshot as JSON."""

    name: str = "GitHubIssueFetcherTool"
    description: str = "Fetch structured GitHub issue context by issue URL or number."

    def _run(self, issue_reference: str = "") -> str:
        if not issue_reference:
            issue_reference = os.getenv("FASTAPI_ISSUE_REF", "").strip()
        issue_data = fetch_issue_snapshot(issue_reference=issue_reference)
        return json.dumps(issue_data, indent=2)


class IssueTriageHeuristicTool(BaseTool):
    """CrewAI tool: deterministic triage scoring from issue JSON."""

    name: str = "IssueTriageHeuristicTool"
    description: str = "Classify issue type/severity/component and return triage JSON."

    def _run(self, issue_context_json: str) -> str:
        issue_data = _safe_json_loads(issue_context_json, default={})
        if not issue_data:
            issue_data = fetch_issue_snapshot(issue_reference=issue_context_json)
        triage = build_baseline_triage(issue_data)
        return json.dumps(triage, indent=2)


class ReproChecklistTool(BaseTool):
    """CrewAI tool: generate reproducibility checklist markdown."""

    name: str = "ReproChecklistTool"
    description: str = "Generate a reproducibility checklist from issue and triage context."

    def _run(self, payload: str) -> str:
        parsed = _safe_json_loads(payload, default={})
        issue_data = parsed.get("issue") or {}
        triage = parsed.get("triage") or {}
        if not issue_data:
            issue_data = fetch_issue_snapshot(payload)
            triage = build_baseline_triage(issue_data)
        return build_repro_checklist(issue_data=issue_data, triage=triage)


class MaintainerReplyDraftTool(BaseTool):
    """CrewAI tool: generate draft maintainer response markdown."""

    name: str = "MaintainerReplyDraftTool"
    description: str = "Draft maintainer response from issue and triage context."

    def _run(self, payload: str) -> str:
        parsed = _safe_json_loads(payload, default={})
        issue_data = parsed.get("issue") or {}
        triage = parsed.get("triage") or {}
        if not issue_data:
            issue_data = fetch_issue_snapshot(payload)
            triage = build_baseline_triage(issue_data)
        return build_draft_reply(issue_data=issue_data, triage=triage)


class OutputSchemaValidatorTool(BaseTool):
    """CrewAI tool: validate triage schema and enforce escalation rule."""

    name: str = "OutputSchemaValidatorTool"
    description: str = "Validate triage schema and normalize required fields."

    def _run(self, triage_json: str) -> str:
        triage = _safe_json_loads(triage_json, default={})
        validated = validate_triage_schema(triage)
        return json.dumps(validated, indent=2)


def get_tools_for_agent(tool_names: List[str]) -> List[Any]:
    """Get tool instances for an agent based on names."""
    if not tool_names:
        return []

    tools: List[Any] = []

    custom_tools = {
        "GitHubIssueFetcherTool": GitHubIssueFetcherTool,
        "IssueTriageHeuristicTool": IssueTriageHeuristicTool,
        "ReproChecklistTool": ReproChecklistTool,
        "MaintainerReplyDraftTool": MaintainerReplyDraftTool,
        "OutputSchemaValidatorTool": OutputSchemaValidatorTool,
    }

    external_tools: Dict[str, Any] = {}
    try:
        from crewai_tools import CodeInterpreterTool, FileReadTool, GithubSearchTool

        external_tools = {
            "GithubSearchTool": GithubSearchTool,
            "CodeInterpreterTool": CodeInterpreterTool,
            "FileReadTool": FileReadTool,
        }
    except ImportError:
        pass

    for tool_name in tool_names:
        tool_cls = custom_tools.get(tool_name) or external_tools.get(tool_name)
        if not tool_cls:
            print(f"Warning: Unknown tool '{tool_name}', skipping")
            continue
        try:
            tools.append(tool_cls())
        except Exception as exc:
            print(f"Warning: Could not instantiate tool '{tool_name}': {exc}")

    return tools
