"""
fastapi_issue_triage Crew Implementation.

This crew combines deterministic heuristics with optional LLM enhancement:
- Always generates triage artifacts from GitHub issue data
- Uses CrewAI agents when LLM credentials are available
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from crewai import Agent, Crew, LLM, Process, Task

from .tools.custom_tools import (
    build_baseline_triage,
    build_draft_reply,
    build_repro_checklist,
    extract_json_from_text,
    extract_markdown_section,
    fetch_issue_snapshot,
    get_tools_for_agent,
    validate_triage_schema,
)


class FastapiIssueTriageCrew:
    """Main crew class for fastapi_issue_triage."""

    def __init__(self):
        """Initialize the crew."""
        self.project_root = Path(__file__).resolve().parents[2]
        self.config_path = self.project_root / "config"
        self.output_base_dir = self.project_root / "outputs"

        self.agents_config = self._load_config("agents.yaml")
        self.tasks_config = self._load_config("tasks.yaml")

        self.initialization_notes = []
        self.llm_mode_enabled = self._llm_mode_enabled()
        self.llm: Optional[LLM] = None
        self.agents: Dict[str, Agent] = {}
        self.tasks: Dict[str, Task] = {}
        self.crew: Optional[Crew] = None

        if self.llm_mode_enabled:
            try:
                self.llm = self._setup_llm()
                if self.llm is None:
                    self.llm_mode_enabled = False
                    self.initialization_notes.append(
                        "LLM mode disabled: provider credentials were not detected."
                    )
                else:
                    self.agents = self._create_agents()
                    self.tasks = self._create_tasks()
                    if self.agents and self.tasks:
                        self.crew = Crew(
                            agents=list(self.agents.values()),
                            tasks=list(self.tasks.values()),
                            process=Process.sequential,
                            verbose=True,
                            memory=False,
                        )
                    else:
                        self.llm_mode_enabled = False
                        self.initialization_notes.append(
                            "LLM mode disabled: could not build full agent/task graph."
                        )
            except Exception as exc:
                self.llm_mode_enabled = False
                self.initialization_notes.append(
                    f"LLM mode disabled due to initialization error: {exc}"
                )
        else:
            self.initialization_notes.append(
                "LLM credentials not found. Running deterministic triage only."
            )

    def _load_config(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration."""
        config_file = self.config_path / filename
        with open(config_file, "r", encoding="utf-8") as file_obj:
            return yaml.safe_load(file_obj)

    def _llm_mode_enabled(self) -> bool:
        """Check if usable LLM configuration is available."""
        provider = os.getenv("agentforge_LLM_PROVIDER", "").strip().lower()
        if provider in {"ollama", "llamacpp"}:
            return bool(os.getenv("agentforge_LLM_MODEL"))
        if provider == "custom":
            return bool(os.getenv("agentforge_LLM_API_KEY") and os.getenv("agentforge_LLM_BASE_URL"))
        return bool(
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("agentforge_LLM_API_KEY")
        )

    def _setup_llm(self) -> Optional[LLM]:
        """Setup LLM configuration for CrewAI."""
        provider = os.getenv("agentforge_LLM_PROVIDER", "").strip().lower()
        model = os.getenv("agentforge_LLM_MODEL", "").strip()
        api_key = os.getenv("agentforge_LLM_API_KEY", "").strip()
        base_url = os.getenv("agentforge_LLM_BASE_URL", "").strip()

        if provider == "custom" and model and api_key and base_url:
            return LLM(
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=0.2,
                max_tokens=1800,
            )

        if provider in {"ollama", "llamacpp"} and model:
            llm_kwargs: Dict[str, Any] = {
                "model": model,
                "temperature": 0.2,
                "max_tokens": 1800,
            }
            if base_url:
                llm_kwargs["base_url"] = base_url
            return LLM(**llm_kwargs)

        if os.getenv("OPENAI_API_KEY"):
            return LLM(model="gpt-4o-mini", temperature=0.2, max_tokens=1800)
        if os.getenv("ANTHROPIC_API_KEY"):
            return LLM(model="claude-3-5-sonnet-20241022", temperature=0.2, max_tokens=1800)
        if os.getenv("GOOGLE_API_KEY"):
            return LLM(model="gemini-1.5-flash", temperature=0.2, max_tokens=1800)

        return None

    def _create_agents(self) -> Dict[str, Agent]:
        """Create agents from config."""
        agents: Dict[str, Agent] = {}
        for agent_name, agent_config in self.agents_config.items():
            tools = get_tools_for_agent(agent_config.get("tools", []))
            try:
                agent = Agent(
                    role=agent_config.get("role", f"Agent {agent_name}"),
                    goal=agent_config.get("goal", "Complete assigned tasks"),
                    backstory=agent_config.get("backstory", "A helpful AI agent"),
                    llm=self.llm,
                    tools=tools,
                    verbose=agent_config.get("verbose", True),
                    allow_delegation=agent_config.get("allow_delegation", False),
                    max_iter=agent_config.get("max_iter", 4),
                )
                agents[agent_name] = agent
            except Exception as exc:
                print(f"Warning: failed to create agent '{agent_name}': {exc}")
        return agents

    def _create_tasks(self) -> Dict[str, Task]:
        """Create tasks from config and wire context dependencies."""
        tasks: Dict[str, Task] = {}
        for task_name, task_config in self.tasks_config.items():
            agent_name = task_config["agent"]
            agent = self.agents.get(agent_name)
            if not agent:
                print(
                    f"Warning: task '{task_name}' skipped because agent '{agent_name}' was not created."
                )
                continue

            tasks[task_name] = Task(
                description=task_config["description"],
                expected_output=task_config["expected_output"],
                agent=agent,
                context=None,
            )

        for task_name, task_config in self.tasks_config.items():
            task_obj = tasks.get(task_name)
            if not task_obj:
                continue
            context_names = task_config.get("context", [])
            context_tasks = [tasks[name] for name in context_names if name in tasks]
            if context_tasks:
                task_obj.context = context_tasks
        return tasks

    def _extract_issue_reference(self, task_input: str) -> str:
        """Extract issue reference from arbitrary input text."""
        raw_input = (task_input or "").strip()
        if not raw_input:
            raise ValueError("Issue reference is required")

        patterns = [
            r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+",
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#\d+",
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+",
            r"#?\d+",
        ]
        for pattern in patterns:
            match = re.search(pattern, raw_input)
            if match:
                return match.group(0)
        raise ValueError("Could not find an issue reference in input.")

    def _inject_runtime_context(
        self, issue_reference: str, issue_data: Dict[str, Any], baseline_triage: Dict[str, Any]
    ):
        """Inject runtime issue context into the main task prompt."""
        if "main_task" not in self.tasks:
            return

        original_description = self.tasks_config["main_task"]["description"]
        payload = {
            "issue_reference": issue_reference,
            "issue_context": issue_data,
            "baseline_triage": baseline_triage,
        }
        payload_json = json.dumps(payload, indent=2)
        runtime_prompt = f"""
{original_description}

Runtime Context:
```json
{payload_json}
```

Return final output in this exact structure:
### TRIAGE_JSON
```json
{{"issue_type":"bug","severity":"medium","component_guess":"other","missing_info":[],"confidence":0.5,"action":"human_review","rationale":"..."}}
```

### REPRO_CHECKLIST_MD
(markdown checklist)

### DRAFT_MAINTAINER_REPLY_MD
(markdown maintainer reply)
"""
        self.tasks["main_task"].description = runtime_prompt.strip()

    def _attempt_llm_enhancement(
        self, issue_reference: str, issue_data: Dict[str, Any], baseline_triage: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run CrewAI agents to enhance deterministic outputs."""
        if not self.crew:
            return {}

        self._inject_runtime_context(
            issue_reference=issue_reference,
            issue_data=issue_data,
            baseline_triage=baseline_triage,
        )
        raw_output = str(self.crew.kickoff())

        triage_section = extract_markdown_section(raw_output, "TRIAGE_JSON")
        triage_json = extract_json_from_text(
            triage_section or raw_output,
            required_keys=["issue_type", "severity", "component_guess"],
        )

        checklist_md = extract_markdown_section(raw_output, "REPRO_CHECKLIST_MD")
        reply_md = extract_markdown_section(raw_output, "DRAFT_MAINTAINER_REPLY_MD")

        return {
            "triage": triage_json,
            "repro_checklist": checklist_md,
            "draft_reply": reply_md,
            "raw_output": raw_output,
        }

    def _write_output_files(
        self,
        issue_data: Dict[str, Any],
        triage: Dict[str, Any],
        repro_checklist: str,
        maintainer_reply: str,
        notes: list[str],
    ) -> Dict[str, str]:
        """Persist output artifacts for this run."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        issue_number = issue_data["issue_number"]
        run_dir = self.output_base_dir / f"issue_{issue_number}_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        triage_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repository": issue_data["repository"],
            "issue_number": issue_number,
            "issue_url": issue_data["issue_url"],
            "triage": triage,
            "notes": notes,
            "issue_summary": {
                "title": issue_data["title"],
                "labels": issue_data["labels"],
                "state": issue_data["state"],
                "comment_count": issue_data["comment_count"],
            },
        }

        triage_file = run_dir / "triage.json"
        checklist_file = run_dir / "repro_checklist.md"
        reply_file = run_dir / "draft_maintainer_reply.md"
        issue_context_file = run_dir / "raw_issue_context.json"

        triage_file.write_text(json.dumps(triage_payload, indent=2), encoding="utf-8")
        checklist_file.write_text(repro_checklist.strip() + "\n", encoding="utf-8")
        reply_file.write_text(maintainer_reply.strip() + "\n", encoding="utf-8")
        issue_context_file.write_text(json.dumps(issue_data, indent=2), encoding="utf-8")

        return {
            "output_dir": str(run_dir),
            "triage_json": str(triage_file),
            "repro_checklist_md": str(checklist_file),
            "draft_reply_md": str(reply_file),
            "raw_issue_context_json": str(issue_context_file),
        }

    def run(self, task_input: str = "") -> str:
        """Run deterministic triage pipeline and optional LLM enhancement."""
        notes = list(self.initialization_notes)
        try:
            issue_reference = self._extract_issue_reference(task_input)
        except ValueError as exc:
            return json.dumps({"status": "failed", "error": str(exc)}, indent=2)

        try:
            issue_data = fetch_issue_snapshot(issue_reference=issue_reference)
        except Exception as exc:
            return json.dumps(
                {
                    "status": "failed",
                    "error": f"Failed to fetch issue data: {exc}",
                    "issue_reference": issue_reference,
                },
                indent=2,
            )

        triage = build_baseline_triage(issue_data)
        repro_checklist = build_repro_checklist(issue_data=issue_data, triage=triage)
        maintainer_reply = build_draft_reply(issue_data=issue_data, triage=triage)
        notes.append("Generated baseline triage/checklist/reply using deterministic heuristics.")

        if self.llm_mode_enabled and self.crew:
            try:
                llm_result = self._attempt_llm_enhancement(
                    issue_reference=issue_reference,
                    issue_data=issue_data,
                    baseline_triage=triage,
                )
                candidate_triage = llm_result.get("triage") or {}
                if candidate_triage:
                    merged = dict(triage)
                    merged.update(candidate_triage)
                    triage = validate_triage_schema(merged)
                    notes.append("Applied LLM triage enhancement.")

                candidate_checklist = (llm_result.get("repro_checklist") or "").strip()
                if candidate_checklist:
                    repro_checklist = candidate_checklist
                    notes.append("Applied LLM repro checklist enhancement.")

                candidate_reply = (llm_result.get("draft_reply") or "").strip()
                if candidate_reply:
                    maintainer_reply = candidate_reply
                    notes.append("Applied LLM reply draft enhancement.")
            except Exception as exc:
                notes.append(f"LLM enhancement skipped due to runtime error: {exc}")

        triage = validate_triage_schema(triage)
        output_paths = self._write_output_files(
            issue_data=issue_data,
            triage=triage,
            repro_checklist=repro_checklist,
            maintainer_reply=maintainer_reply,
            notes=notes,
        )

        summary = {
            "status": "completed",
            "repository": issue_data["repository"],
            "issue_number": issue_data["issue_number"],
            "issue_url": issue_data["issue_url"],
            "triage": triage,
            "files": output_paths,
            "notes": notes,
        }
        return json.dumps(summary, indent=2)

    def get_crew_info(self) -> Dict[str, Any]:
        """Get static info about the crew."""
        return {
            "name": "fastapi_issue_triage",
            "description": "GitHub issue triage and maintainer response copilot for tiangolo/fastapi.",
            "agents": list(self.agents.keys()),
            "tasks": list(self.tasks.keys()),
            "process_type": "sequential",
            "llm_mode_enabled": self.llm_mode_enabled,
        }

