#!/usr/bin/env python3
"""Build a unified benchmark manifest for adaptive attack evaluation.

The manifest is intentionally defense-oriented: every row exposes normalized
text fields, step candidates, and provenance/source-sink metadata so that
step-level guards, prompt-injection detectors, data filters, and IFC-style
defenses can consume the same data layer.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "experiment-stage" / "adaptive_attack_eval"
MANIFEST_PATH = OUT_DIR / "benchmark_manifest.jsonl"
SUMMARY_PATH = OUT_DIR / "benchmark_manifest_summary.json"
ATTACK_CATEGORY_TABLE_PATH = OUT_DIR / "benchmark_attack_category_table.md"

SCHEMA_VERSION = "adaptive_attack_eval.benchmark_manifest.v1"
ACTION_RE = re.compile(r"\(2\)\s*Action:\s*([^\n]+)")
ACTION_INPUT_RE = re.compile(r"\(3\)\s*Action Input:\s*(\{.*\})", re.DOTALL)
INFORMATION_RE = re.compile(r"<INFORMATION>.*?</INFORMATION>", re.DOTALL)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def short_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def text_field(name: str, text: str | None, *, trust: str, source: str) -> dict[str, Any]:
    return {
        "name": name,
        "text": text or "",
        "trust": trust,
        "source": source,
    }


def taxonomy_labels(
    risk_categories: list[str],
    *,
    rationale: str | None = None,
    review_status: str = "auto",
    review_reasons: list[str] | None = None,
) -> dict[str, Any]:
    risk_set = set(risk_categories)
    primary = risk_categories[0] if risk_categories else "unknown"
    return {
        "clean": "yes" if "clean" in risk_set else "no",
        "value": "yes" if "value" in risk_set else "no",
        "authority": "yes" if "authority" in risk_set else "no",
        "policy": "yes" if "policy" in risk_set else "no",
        "primary": primary,
        "rationale": rationale or default_taxonomy_rationale(risk_categories),
        "review_status": review_status,
        "review_reasons": review_reasons or [],
    }


def default_taxonomy_rationale(risk_categories: list[str]) -> str:
    if risk_categories == ["clean"]:
        return "Official benign/clean row; no authority, value, or policy violation is labeled."
    if not risk_categories:
        return "No taxonomy category was assigned."
    pieces = []
    if "authority" in risk_categories:
        pieces.append("authority=yes because the row involves action authorization or control by a non-user or insufficiently authorized source")
    if "value" in risk_categories:
        pieces.append("value=yes because protected action arguments or sink payloads are implicated")
    if "policy" in risk_categories:
        pieces.append("policy=yes because trusted user intent or official harmful-behavior labels request disallowed harm")
    return "; ".join(pieces) + "."


def base_row(
    *,
    benchmark: str,
    suite: str,
    source_path: str,
    split: str,
    surface: str,
    risk_categories: list[str],
    controlled_fields: list[str],
    clean_input: str,
    attacked_input: str,
    text_fields: list[dict[str, Any]],
    step_candidate: dict[str, Any],
    provenance: dict[str, Any],
    target: dict[str, Any],
    judge: dict[str, Any],
    compatible_defenses: list[str],
    attack_baselines: list[str],
    raw_ref: dict[str, Any] | None = None,
    taxonomy_rationale: str | None = None,
    taxonomy_review_status: str = "auto",
    taxonomy_review_reasons: list[str] | None = None,
    notes: str = "",
    status: str = "ready",
) -> dict[str, Any]:
    seed = {
        "benchmark": benchmark,
        "suite": suite,
        "source_path": source_path,
        "split": split,
        "surface": surface,
        "risk_categories": risk_categories,
        "controlled_fields": controlled_fields,
        "clean_input": clean_input,
        "attacked_input": attacked_input,
        "target": target,
        "raw_ref": raw_ref,
    }
    case_id = f"{benchmark.lower()}::{suite.lower()}::{surface.lower()}::{short_hash(seed)}"
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "benchmark": benchmark,
        "suite": suite,
        "source_path": source_path,
        "split": split,
        "status": status,
        "surface": surface,
        "primary_attack_category": risk_categories[0] if risk_categories else "unknown",
        "risk_categories": risk_categories,
        "taxonomy_labels": taxonomy_labels(
            risk_categories,
            rationale=taxonomy_rationale,
            review_status=taxonomy_review_status,
            review_reasons=taxonomy_review_reasons,
        ),
        "controlled_fields": controlled_fields,
        "clean_input": clean_input,
        "attacked_input": attacked_input,
        "text_fields": text_fields,
        "step_candidate": step_candidate,
        "provenance": provenance,
        "target": target,
        "judge": judge,
        "compatible_defenses": compatible_defenses,
        "attack_baselines": attack_baselines,
        "raw_ref": raw_ref or {},
        "notes": notes,
    }


VALUE_FLOW_KEYWORDS = [
    "account",
    "address",
    "amount",
    "api key",
    "attachment",
    "bank",
    "card",
    "content",
    "credential",
    "data",
    "database",
    "delete",
    "domain",
    "email",
    "exfiltrat",
    "file",
    "iban",
    "key",
    "leak",
    "link",
    "message",
    "password",
    "payload",
    "phone",
    "post",
    "recipient",
    "record",
    "secret",
    "send",
    "subject",
    "token",
    "transfer",
    "upload",
    "url",
    "write",
]

VALUE_FLOW_TOOL_KEYWORDS = [
    "delete",
    "email",
    "extract",
    "grant",
    "message",
    "post",
    "send",
    "transfer",
    "update",
    "upload",
    "write",
]


def has_value_flow_signal(text: str, tool_name: str | None = None) -> bool:
    lowered = f"{text}\n{tool_name or ''}".lower()
    return any(keyword in lowered for keyword in VALUE_FLOW_KEYWORDS + VALUE_FLOW_TOOL_KEYWORDS)


def classify_external_injection_risk(text: str, tool_name: str | None = None) -> list[str]:
    """Classify attacker-controlled external content, not trusted user intent.

    External injections are authority by default. They become value-primary when
    the injected content appears to control a protected action argument or sink
    payload, such as a recipient, URL, account, file, message, or transfer.
    """
    if has_value_flow_signal(text, tool_name):
        return ["value", "authority"]
    return ["authority"]


def authority_primary_external_injection_risk(text: str, tool_name: str | None = None) -> list[str]:
    categories = classify_external_injection_risk(text, tool_name)
    if "authority" not in categories:
        categories.append("authority")
    return ["authority"] + [category for category in categories if category != "authority"]


def classify_user_policy_risk(text: str) -> list[str]:
    """Classify trusted/user-originated harmful requests."""
    categories = ["policy"]
    if has_value_flow_signal(text):
        categories.append("value")
    return categories


TOOLSAFE_VALUE_RISKS = {
    "Lead to property loss",
    "Leak sensitive data / information",
    "Compromise availability",
}

TOOLSAFE_POLICY_RISKS = {
    "Spread unsafe information / misinformation",
    "Produce unsafe information / misinformation",
    "Contribute to harmful / vulnerable code",
    "Violate law or ethics / damage society",
    "Lead to physical harm",
}


def classify_toolsafe_agentsafetybench(item: dict[str, Any]) -> list[str]:
    risks = set(item.get("risks") or [])
    categories: list[str] = []
    if item.get("fulfillable") in [1, "1"]:
        categories.append("authority")
    if risks & TOOLSAFE_VALUE_RISKS:
        categories.append("value")
    if risks & TOOLSAFE_POLICY_RISKS:
        categories.append("policy")
    if not categories:
        categories.append("policy")
    return list(dict.fromkeys(categories))


def extract_action(current_action: str) -> tuple[str | None, dict[str, Any]]:
    action_match = ACTION_RE.search(current_action or "")
    tool_name = action_match.group(1).strip() if action_match else None
    args: dict[str, Any] = {}
    input_match = ACTION_INPUT_RE.search(current_action or "")
    if input_match:
        raw = input_match.group(1).strip()
        try:
            args = json.loads(raw)
        except Exception:
            args = {"_raw": raw}
    return tool_name, args


def build_asb_rows() -> list[dict[str, Any]]:
    task_path = ROOT / "benchmarks" / "ASB" / "data" / "agent_task.jsonl"
    tool_path = ROOT / "benchmarks" / "ASB" / "data" / "all_attack_tools.jsonl"
    if not task_path.exists():
        task_path = ROOT / "benchmarks" / "ASB" / "data" / "agent_task_test.jsonl"
    if not tool_path.exists():
        tool_path = ROOT / "benchmarks" / "ASB" / "data" / "attack_tools_test.jsonl"

    tasks_by_agent: dict[str, list[str]] = {}
    for row in load_jsonl(task_path):
        tasks_by_agent[row["agent_name"]] = list(row.get("tasks") or [])

    rows: list[dict[str, Any]] = []
    for idx, tool in enumerate(load_jsonl(tool_path)):
        agent = tool.get("Corresponding Agent") or "unknown_agent"
        tasks = tasks_by_agent.get(agent) or [""]
        attacker_instruction = tool.get("Attacker Instruction") or ""
        description = tool.get("Description") or ""
        attack_type = tool.get("Attack Type") or ""
        for task_idx, task in enumerate(tasks):
            common = {
                "benchmark": "ASB",
                "suite": agent,
                "source_path": str(tool_path.relative_to(ROOT)),
                "split": "full" if tool_path.name == "all_attack_tools.jsonl" else "test",
                "clean_input": task,
                "target": {
                    "type": "malicious_tool_or_goal",
                    "tool_name": tool.get("Attacker Tool"),
                    "goal": tool.get("Attack goal"),
                    "attack_type": attack_type,
                },
                "judge": {"type": "official_or_rollout", "name": "ASB evaluator"},
                "compatible_defenses": [
                    "ASB_official_configs",
                    "TS-Guard",
                    "PromptGuard2_LlamaFirewall",
                    "DataFilter",
                    "FIDES_deferred",
                ],
                "attack_baselines": ["ASB_official_attacks", "PAIR", "TAP"],
                "raw_ref": {"agent": agent, "tool_index": idx, "task_index": task_idx},
            }
            rows.append(
                base_row(
                    **common,
                    surface="DPI",
                    risk_categories=classify_user_policy_risk(f"{attacker_instruction}\n{tool.get('Attack goal') or ''}"),
                    taxonomy_rationale=(
                        "ASB DPI puts the malicious instruction in the direct user prompt; this is treated as malicious user "
                        "intent for the policy surface, with value=yes when the prompt/tool goal mentions protected sink values."
                    ),
                    controlled_fields=["user_prompt"],
                    attacked_input=f"{task}\n\n{attacker_instruction}",
                    text_fields=[
                        text_field("user_prompt.clean", task, trust="trusted_user", source="ASB task"),
                        text_field("user_prompt.attack", attacker_instruction, trust="attacker_controlled", source="ASB attacker instruction"),
                    ],
                    step_candidate={
                        "available": True,
                        "tool_name": tool.get("Attacker Tool"),
                        "tool_args": {},
                        "thought": attacker_instruction,
                        "source": "constructed_from_ASB_attack_tool",
                    },
                    provenance={
                        "source_type": "user_prompt",
                        "source_trust": "attacker_controlled",
                        "sink_type": "tool_call",
                        "target_sink": tool.get("Attacker Tool"),
                        "value_flow": "candidate",
                    },
                    notes="ASB direct prompt injection control field.",
                )
            )
            rows.append(
                base_row(
                    **common,
                    surface="OPI",
                    risk_categories=authority_primary_external_injection_risk(
                        f"{attacker_instruction}\n{tool.get('Attack goal') or ''}",
                        tool.get("Attacker Tool"),
                    ),
                    taxonomy_rationale=(
                        "ASB OPI places attacker-controlled instructions in a tool observation; authority=yes because an "
                        "unauthorized external source can control the agent action, and value=yes when the injected text or "
                        "target tool suggests protected action arguments or sink payloads."
                    ),
                    taxonomy_review_status="needs_review",
                    taxonomy_review_reasons=["ASB OPI value-vs-authority split is inferred from tool/text keywords, not an official per-row value-flow label."],
                    controlled_fields=["tool_observation"],
                    attacked_input=attacker_instruction,
                    text_fields=[
                        text_field("user_prompt.clean", task, trust="trusted_user", source="ASB task"),
                        text_field("tool_observation.attack", attacker_instruction, trust="attacker_controlled", source="ASB attacker instruction"),
                    ],
                    step_candidate={
                        "available": True,
                        "tool_name": tool.get("Attacker Tool"),
                        "tool_args": {},
                        "thought": f"Following injected observation: {attacker_instruction}",
                        "source": "constructed_from_ASB_attack_tool",
                    },
                    provenance={
                        "source_type": "tool_observation",
                        "source_trust": "attacker_controlled",
                        "sink_type": "tool_call",
                        "target_sink": tool.get("Attacker Tool"),
                        "value_flow": "candidate",
                    },
                    notes="ASB indirect prompt injection over tool observation.",
                )
            )
            rows.append(
                base_row(
                    **common,
                    surface="PoT",
                    risk_categories=authority_primary_external_injection_risk(
                        f"{description}\n{attacker_instruction}\n{tool.get('Attack goal') or ''}",
                        tool.get("Attacker Tool"),
                    ),
                    taxonomy_rationale=(
                        "ASB PoT makes the attacker-controlled tool spec or trigger influence tool selection/action; "
                        "authority=yes by construction, and value=yes when the tool spec or goal controls protected arguments or payloads."
                    ),
                    taxonomy_review_status="needs_review",
                    taxonomy_review_reasons=["ASB PoT value-vs-authority split is inferred from tool/text keywords, not an official per-row value-flow label."],
                    controlled_fields=["tool_name", "tool_description", "tool_trigger"],
                    attacked_input=f"{tool.get('Attacker Tool')}: {description}\nTrigger: {attacker_instruction}",
                    text_fields=[
                        text_field("user_prompt.clean", task, trust="trusted_user", source="ASB task"),
                        text_field("tool_spec.attack", f"{description}\n{attacker_instruction}", trust="attacker_controlled", source="ASB attack tool"),
                    ],
                    step_candidate={
                        "available": True,
                        "tool_name": tool.get("Attacker Tool"),
                        "tool_args": {},
                        "thought": "Tool specification may induce malicious tool use.",
                        "source": "ASB_prompt_as_tool",
                    },
                    provenance={
                        "source_type": "tool_spec",
                        "source_trust": "attacker_controlled",
                        "sink_type": "tool_selection",
                        "target_sink": tool.get("Attacker Tool"),
                        "value_flow": "candidate",
                    },
                    notes="ASB prompt-as-tool / tool trigger surface.",
                )
            )
    return rows


def build_adaptive_attack_agent_rows() -> list[dict[str, Any]]:
    data_dir = ROOT / "benchmarks" / "AdaptiveAttackAgent" / "InjecAgent" / "data"
    files = [
        ("direct_harm_base", "test_cases_dh_base.json", ["authority"]),
        ("data_stealing_base", "test_cases_ds_base.json", ["authority", "value"]),
        ("direct_harm_enhanced", "test_cases_dh_enhanced.json", ["authority"]),
        ("data_stealing_enhanced", "test_cases_ds_enhanced.json", ["authority", "value"]),
    ]
    rows: list[dict[str, Any]] = []
    for suite, filename, risk in files:
        path = data_dir / filename
        if not path.exists():
            continue
        for idx, item in enumerate(load_json(path)):
            user_instruction = item.get("User Instruction") or ""
            attacker_instruction = item.get("Attacker Instruction") or ""
            tool_response = item.get("Tool Response") or item.get("Tool Response Template") or ""
            target_tools = item.get("Attacker Tools") or []
            target_tool = target_tools[0] if target_tools else None
            rows.append(
                base_row(
                    benchmark="AdaptiveAttackAgent",
                    suite=f"InjecAgent_{suite}",
                    source_path=str(path.relative_to(ROOT)),
                    split="enhanced" if "enhanced" in path.name else "base",
                    surface="OPI",
                    risk_categories=risk,
                    taxonomy_rationale=(
                        "AdaptiveAttackAgent/InjecAgent rows are indirect tool-response attacks. data_stealing suites are "
                        "value-primary; direct_harm suites are authority-primary because the harmful objective comes from an "
                        "external injected tool response rather than trusted user intent."
                    ),
                    controlled_fields=["tool_observation", "tool_response_template"],
                    clean_input=user_instruction,
                    attacked_input=tool_response or attacker_instruction,
                    text_fields=[
                        text_field("user_prompt.clean", user_instruction, trust="trusted_user", source="InjecAgent user case"),
                        text_field("tool_observation.attack", tool_response or attacker_instruction, trust="attacker_controlled", source="InjecAgent injected tool response"),
                    ],
                    step_candidate={
                        "available": True,
                        "tool_name": target_tool,
                        "tool_args": {},
                        "thought": item.get("Thought") or attacker_instruction,
                        "source": "InjecAgent target attacker tool",
                    },
                    provenance={
                        "source_type": "tool_observation",
                        "source_trust": "attacker_controlled",
                        "sink_type": "tool_call",
                        "target_sink": target_tool,
                        "value_flow": "candidate",
                    },
                    target={
                        "type": "attacker_tool_execution",
                        "tool_name": target_tool,
                        "tools": target_tools,
                        "goal": attacker_instruction,
                        "expected_achievements": item.get("Expected Achievements"),
                    },
                    judge={"type": "official_or_rollout", "name": "AdaptiveAttackAgent evaluator"},
                    compatible_defenses=[
                        "AdaptiveAttackAgent_official_configs",
                        "PromptGuard2_LlamaFirewall",
                        "DataFilter",
                        "TS-Guard",
                        "FIDES_deferred",
                    ],
                    attack_baselines=["GCG", "MGCG_ST", "MGCG_DT", "TGCG", "PAIR", "TAP"],
                    raw_ref={"index": idx, "attack_type": item.get("Attack Type"), "user_tool": item.get("User Tool")},
                    notes="Official InjecAgent indirect prompt injection case.",
                )
            )
    return rows


def literal_eval_expr(node: ast.AST, scope: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return scope.get(node.id, f"${node.id}")
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                parts.append(str(literal_eval_expr(value.value, scope)))
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return str(literal_eval_expr(node.left, scope)) + str(literal_eval_expr(node.right, scope))
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def extract_agentdojo_goals(path: Path) -> list[dict[str, Any]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or not node.name.startswith("InjectionTask"):
            continue
        scope: dict[str, Any] = {}
        goal = None
        difficulty = None
        target_functions: list[str] = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        value = literal_eval_expr(stmt.value, scope)
                        scope[target.id] = value
                        if target.id == "GOAL":
                            goal = value
                        if target.id == "DIFFICULTY":
                            difficulty = ast.unparse(stmt.value) if hasattr(ast, "unparse") else None
            elif isinstance(stmt, ast.FunctionDef) and stmt.name == "ground_truth":
                source = ast.get_source_segment(path.read_text(encoding="utf-8"), stmt) or ""
                target_functions = sorted(set(part.split('"')[1] for part in source.split("function=")[1:] if '"' in part))
        if goal:
            out.append(
                {
                    "class_name": node.name,
                    "goal": str(goal),
                    "difficulty": difficulty,
                    "target_functions": target_functions,
                }
            )
    return out


def build_agentdojo_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    suites = ["banking", "slack", "travel", "workspace"]
    for suite in suites:
        path = ROOT / "benchmarks" / "agentdojo" / "src" / "agentdojo" / "default_suites" / "v1" / suite / "injection_tasks.py"
        if not path.exists():
            continue
        for item in extract_agentdojo_goals(path):
            goal = item["goal"]
            target_functions = item.get("target_functions") or []
            first_function = target_functions[0] if target_functions else None
            rows.append(
                base_row(
                    benchmark="AgentDojo",
                    suite=suite,
                    source_path=str(path.relative_to(ROOT)),
                    split="v1",
                    surface="OPI",
                    risk_categories=authority_primary_external_injection_risk(goal, first_function),
                    taxonomy_rationale=(
                        "AgentDojo static injection tasks put attacker-controlled content in untrusted environment data; "
                        "authority=yes by construction, and value=yes when the target function or goal indicates protected sink values."
                    ),
                    taxonomy_review_status="needs_review",
                    taxonomy_review_reasons=["AgentDojo static value-vs-authority split is inferred from target function/goal text after static extraction."],
                    controlled_fields=["untrusted_tool_or_content"],
                    clean_input="AgentDojo user task selected by suite runner.",
                    attacked_input=goal,
                    text_fields=[
                        text_field("user_prompt.clean", "AgentDojo user task selected by suite runner.", trust="trusted_user", source="AgentDojo user task"),
                        text_field("untrusted_content.attack", goal, trust="attacker_controlled", source="AgentDojo injection task GOAL"),
                    ],
                    step_candidate={
                        "available": bool(target_functions),
                        "tool_name": first_function,
                        "tool_args": {},
                        "thought": goal,
                        "source": "AgentDojo injection ground_truth static extraction",
                    },
                    provenance={
                        "source_type": "untrusted_content",
                        "source_trust": "attacker_controlled",
                        "sink_type": "tool_call_or_environment_mutation",
                        "target_sink": target_functions,
                        "value_flow": "candidate",
                    },
                    target={
                        "type": "injection_task_success",
                        "tool_name": first_function,
                        "functions": target_functions,
                        "goal": goal,
                    },
                    judge={"type": "official_or_rollout", "name": "AgentDojo injection_task.security"},
                    compatible_defenses=[
                        "AgentDojo_builtin_configs",
                        "PromptGuard2_LlamaFirewall",
                        "DataFilter",
                        "TS-Guard",
                        "FIDES_deferred",
                    ],
                    attack_baselines=["AgentDojo_official_attacks", "PAIR", "TAP"],
                    raw_ref={"class_name": item["class_name"], "difficulty": item.get("difficulty")},
                    notes="Static AgentDojo injection task row; runner must pair it with compatible user tasks.",
                )
            )
    return rows


def build_agentdojo_tsbench_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    data_dir = ROOT / "benchmarks" / "ToolSafe" / "TS-Bench" / "agentdojo-traj"
    if not data_dir.exists():
        return rows
    for path in sorted(data_dir.glob("*.json")):
        suite = path.stem
        for idx, item in enumerate(load_json(path)):
            instruction = item.get("instruction") or ""
            history = item.get("history") or ""
            current_action = item.get("current_action") or ""
            env_info = item.get("env_info") or ""
            tool_name, tool_args = extract_action(current_action)
            is_attack = item.get("score") in [1, 1.0, "1"]
            info_match = INFORMATION_RE.search(history)
            attack_span = info_match.group(0) if info_match else ""
            risk = (
                authority_primary_external_injection_risk(f"{attack_span or history}\n{current_action}", tool_name)
                if is_attack
                else ["clean"]
            )
            rows.append(
                base_row(
                    benchmark="AgentDojo",
                    suite=f"TS-Bench/{suite}",
                    source_path=str(path.relative_to(ROOT)),
                    split="ts_bench_traj",
                    surface="Step",
                    risk_categories=risk,
                    taxonomy_rationale=(
                        "TS-Bench AgentDojo score=0 rows are clean. score=1 rows are injected-context step attacks; "
                        "authority/value labels are inferred from the attack span, current action, and tool name."
                    ),
                    taxonomy_review_status="needs_review" if is_attack else "auto",
                    taxonomy_review_reasons=(
                        ["TS-Bench AgentDojo attack rows do not carry official authority-vs-value labels; split is inferred from current action and injected span."]
                        if is_attack
                        else []
                    ),
                    controlled_fields=["tool_observation"] if attack_span else ["interaction_history"],
                    clean_input=instruction,
                    attacked_input=attack_span or history,
                    text_fields=[
                        text_field("user_prompt.clean", instruction, trust="trusted_user", source="TS-Bench AgentDojo trajectory"),
                        text_field(
                            "interaction_history",
                            history,
                            trust="attacker_controlled" if attack_span else "mixed_or_prior_context",
                            source="TS-Bench AgentDojo trajectory",
                        ),
                        text_field("current_action", current_action, trust="agent_generated", source="TS-Bench AgentDojo trajectory"),
                    ],
                    step_candidate={
                        "available": bool(tool_name),
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "thought": current_action,
                        "source": "TS-Bench AgentDojo current_action",
                    },
                    provenance={
                        "source_type": "tool_observation" if attack_span else "interaction_history",
                        "source_trust": "attacker_controlled" if attack_span else "mixed_or_prior_context",
                        "sink_type": "tool_call",
                        "target_sink": tool_name,
                        "value_flow": "candidate" if is_attack else "clean_or_unknown",
                    },
                    target={
                        "type": "ts_bench_step_label",
                        "label_score": item.get("score"),
                        "tool_name": tool_name,
                        "suite": suite,
                    },
                    judge={"type": "official_or_step_guard", "name": "TS-Bench AgentDojo step label / TS-Guard"},
                    compatible_defenses=[
                        "AgentDojo_builtin_configs",
                        "TS-Guard",
                        "PromptGuard2_LlamaFirewall",
                        "DataFilter",
                        "FIDES_deferred",
                    ],
                    attack_baselines=["AgentDojo_official_attacks", "PAIR", "TAP"],
                    raw_ref={
                        "id_interaction": item.get("id-interaction"),
                        "id_segment": item.get("id-segment"),
                        "index": idx,
                        "score": item.get("score"),
                    },
                    notes="TS-Bench AgentDojo trajectory row used by TS-Guard-style step evaluation.",
                )
            )
    return rows


def build_toolsafe_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    asb_path = ROOT / "benchmarks" / "ToolSafe" / "benchmark" / "agent_safetybench" / "data" / "released_data.json"
    if asb_path.exists():
        for item in load_json(asb_path):
            instruction = item.get("instruction") or ""
            tools = []
            for env in item.get("environments") or []:
                tools.extend(env.get("tools") or [])
            rows.append(
                base_row(
                    benchmark="ToolSafe",
                    suite="agent_safetybench",
                    source_path=str(asb_path.relative_to(ROOT)),
                    split="released",
                    surface="Step",
                    risk_categories=classify_toolsafe_agentsafetybench(item),
                    taxonomy_rationale=(
                        "ToolSafe AgentSafetyBench uses official risks plus fulfillable. fulfillable=1 is authority-primary "
                        "because the tool action is executable but safety/authorization boundaries are implicated; official "
                        "property/sensitive-data/availability risks add value=yes; official misinformation/harmful-code/"
                        "law-ethics/physical-harm risks add policy=yes."
                    ),
                    controlled_fields=["user_prompt", "environment_spec"],
                    clean_input="",
                    attacked_input=instruction,
                    text_fields=[
                        text_field("user_prompt.attack_or_task", instruction, trust="user_supplied", source="ToolSafe AgentSafetyBench"),
                    ],
                    step_candidate={
                        "available": bool(tools),
                        "tool_name": tools[0] if tools else None,
                        "tool_args": {},
                        "thought": instruction,
                        "source": "ToolSafe AgentSafetyBench environment tools",
                    },
                    provenance={
                        "source_type": "user_prompt",
                        "source_trust": "user_supplied",
                        "sink_type": "tool_call",
                        "target_sink": tools,
                        "value_flow": "unknown",
                    },
                    target={
                        "type": "unsafe_or_unfulfillable_tool_task",
                        "tool_name": tools[0] if tools else None,
                        "tools": tools,
                        "risks": item.get("risks"),
                        "failure_modes": item.get("failure_modes"),
                    },
                    judge={"type": "official_or_step_guard", "name": "ToolSafe / TS-Bench evaluator"},
                    compatible_defenses=["TS-Guard", "PromptGuard2_LlamaFirewall", "DataFilter", "FIDES_deferred"],
                    attack_baselines=["ToolSafe_official", "PAIR", "TAP"],
                    raw_ref={"id": item.get("id")},
                    notes="ToolSafe AgentSafetyBench released task.",
                )
            )

    tsbench_agentharm_dir = ROOT / "benchmarks" / "ToolSafe" / "TS-Bench" / "agentharm-traj"
    for filename, risk, suite, note in [
        ("harmful_steps.json", ["policy"], "TS-Bench/AgentHarm_harmful_steps", "TS-Bench AgentHarm harmful step trajectory."),
        ("benign_steps.json", ["clean"], "TS-Bench/AgentHarm_benign_steps", "TS-Bench AgentHarm benign step trajectory for clean false-block evaluation."),
    ]:
        path = tsbench_agentharm_dir / filename
        if not path.exists():
            continue
        for idx, item in enumerate(load_json(path)):
            instruction = item.get("instruction") or ""
            history = item.get("history") or ""
            current_action = item.get("current_action") or ""
            env_info = item.get("env_info") or ""
            tool_name, tool_args = extract_action(current_action)
            rows.append(
                base_row(
                    benchmark="ToolSafe",
                    suite=suite,
                    source_path=str(path.relative_to(ROOT)),
                    split="ts_bench_traj",
                    surface="Step",
                    risk_categories=risk,
                    taxonomy_rationale=(
                        "TS-Bench AgentHarm harmful steps are trusted-user harmful requests and therefore policy-primary; "
                        "benign steps are clean false-block controls."
                    ),
                    controlled_fields=["user_prompt", "tool_args"],
                    clean_input=instruction if risk == ["clean"] else "",
                    attacked_input=instruction if risk != ["clean"] else "",
                    text_fields=[
                        text_field(
                            "user_prompt.clean" if risk == ["clean"] else "user_prompt.attack_or_task",
                            instruction,
                            trust="trusted_user" if risk == ["clean"] else "user_supplied",
                            source="TS-Bench AgentHarm trajectory",
                        ),
                        text_field("interaction_history", history, trust="mixed_or_prior_context", source="TS-Bench AgentHarm trajectory"),
                        text_field("current_action", current_action, trust="agent_generated", source="TS-Bench AgentHarm trajectory"),
                    ],
                    step_candidate={
                        "available": bool(tool_name),
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "thought": current_action,
                        "source": "TS-Bench AgentHarm current_action",
                    },
                    provenance={
                        "source_type": "user_prompt" if risk != ["clean"] else "trusted_user_prompt",
                        "source_trust": "user_supplied" if risk != ["clean"] else "trusted_user",
                        "sink_type": "tool_call",
                        "target_sink": tool_name,
                        "value_flow": "candidate" if risk != ["clean"] else "clean",
                    },
                    target={
                        "type": "ts_bench_agentharm_step_label",
                        "label_score": item.get("score"),
                        "tool_name": tool_name,
                    },
                    judge={"type": "official_or_step_guard", "name": "TS-Bench AgentHarm step label / TS-Guard"},
                    compatible_defenses=["TS-Guard", "PromptGuard2_LlamaFirewall", "DataFilter", "FIDES_deferred"],
                    attack_baselines=["AgentHarm_official", "HarmBench_attacks", "PAIR", "TAP"] if risk != ["clean"] else ["AgentHarm_benign_clean"],
                    raw_ref={
                        "id_interaction": item.get("id-interaction"),
                        "id_segment": item.get("id-segment"),
                        "index": idx,
                        "score": item.get("score"),
                    },
                    notes=note,
                )
            )

    agentharm_path = ROOT / "benchmarks" / "ToolSafe" / "benchmark" / "agentharm" / "dataset" / "harmful_behaviors_test_public.json"
    if agentharm_path.exists():
        data = load_json(agentharm_path)
        for item in data.get("behaviors", []):
            prompt = item.get("prompt") or ""
            functions = item.get("target_functions") or []
            rows.append(
                base_row(
                    benchmark="ToolSafe",
                    suite="AgentHarm",
                    source_path=str(agentharm_path.relative_to(ROOT)),
                    split="test_public",
                    surface="Step",
                    risk_categories=["policy"],
                    taxonomy_rationale="AgentHarm public harmful behaviors are trusted-user harmful tool-use requests, so policy=yes.",
                    controlled_fields=["user_prompt"],
                    clean_input="",
                    attacked_input=prompt,
                    text_fields=[
                        text_field("user_prompt.attack_or_task", prompt, trust="user_supplied", source="AgentHarm public behavior"),
                    ],
                    step_candidate={
                        "available": bool(functions),
                        "tool_name": functions[0] if functions else None,
                        "tool_args": {},
                        "thought": prompt,
                        "source": "AgentHarm target_functions",
                    },
                    provenance={
                        "source_type": "user_prompt",
                        "source_trust": "user_supplied",
                        "sink_type": "tool_call_sequence",
                        "target_sink": functions,
                        "value_flow": "unknown",
                    },
                    target={
                        "type": "harmful_tool_sequence",
                        "tool_name": functions[0] if functions else None,
                        "tools": functions,
                        "category": item.get("category"),
                        "grading_function": item.get("grading_function"),
                    },
                    judge={"type": "official", "name": "AgentHarm grading_function"},
                    compatible_defenses=["TS-Guard", "PromptGuard2_LlamaFirewall", "DataFilter", "FIDES_deferred"],
                    attack_baselines=["AgentHarm_official", "PAIR", "TAP", "HarmBench_attacks"],
                    raw_ref={"id": item.get("id"), "id_original": item.get("id_original")},
                    notes="AgentHarm public harmful behavior in ToolSafe tree.",
                )
            )
    benign_agentharm_path = ROOT / "benchmarks" / "ToolSafe" / "benchmark" / "agentharm" / "dataset" / "benign_behaviors_test_public.json"
    if benign_agentharm_path.exists():
        data = load_json(benign_agentharm_path)
        for item in data.get("behaviors", []):
            prompt = item.get("prompt") or ""
            functions = item.get("target_functions") or []
            rows.append(
                base_row(
                    benchmark="ToolSafe",
                    suite="AgentHarm_benign",
                    source_path=str(benign_agentharm_path.relative_to(ROOT)),
                    split="test_public",
                    surface="Step",
                    risk_categories=["clean"],
                    taxonomy_rationale="AgentHarm public benign behaviors are authorized clean tool-use requests.",
                    controlled_fields=["user_prompt"],
                    clean_input=prompt,
                    attacked_input="",
                    text_fields=[
                        text_field("user_prompt.clean", prompt, trust="trusted_user", source="AgentHarm public benign behavior"),
                    ],
                    step_candidate={
                        "available": bool(functions),
                        "tool_name": functions[0] if functions else None,
                        "tool_args": {},
                        "thought": prompt,
                        "source": "AgentHarm benign target_functions",
                    },
                    provenance={
                        "source_type": "user_prompt",
                        "source_trust": "trusted_user",
                        "sink_type": "tool_call_sequence",
                        "target_sink": functions,
                        "value_flow": "clean",
                    },
                    target={
                        "type": "benign_tool_sequence",
                        "tool_name": functions[0] if functions else None,
                        "tools": functions,
                        "category": item.get("category"),
                        "grading_function": item.get("grading_function"),
                    },
                    judge={"type": "official", "name": "AgentHarm benign grading_function"},
                    compatible_defenses=["TS-Guard", "PromptGuard2_LlamaFirewall", "DataFilter", "FIDES_deferred"],
                    attack_baselines=["AgentHarm_benign_clean"],
                    raw_ref={"id": item.get("id"), "id_original": item.get("id_original")},
                    notes="AgentHarm public benign behavior for clean false-block evaluation.",
                )
            )
    return rows


def build_harmbench_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    data_dir = ROOT / "benchmarks" / "HarmBench" / "data"
    behavior_dir = data_dir / "behavior_datasets"
    target_text_path = data_dir / "optimizer_targets" / "harmbench_targets_text.json"
    target_mm_path = data_dir / "optimizer_targets" / "harmbench_targets_multimodal.json"
    targets_text = load_json(target_text_path) if target_text_path.exists() else {}
    targets_mm = load_json(target_mm_path) if target_mm_path.exists() else {}

    text_path = behavior_dir / "harmbench_behaviors_text_all.csv"
    for idx, item in enumerate(load_csv(text_path)):
        behavior = item.get("Behavior") or ""
        behavior_id = item.get("BehaviorID") or f"text_{idx}"
        context = item.get("ContextString") or ""
        attacked_input = f"{context}\n\n{behavior}".strip() if context else behavior
        rows.append(
            base_row(
                benchmark="HarmBench",
                suite="text_all",
                source_path=str(text_path.relative_to(ROOT)),
                split="all",
                surface="DPI",
                risk_categories=["policy"],
                taxonomy_rationale="HarmBench text behavior rows are direct trusted-user harmful requests, so policy=yes.",
                controlled_fields=["user_prompt"],
                clean_input="",
                attacked_input=attacked_input,
                text_fields=[
                    text_field("user_prompt.attack", attacked_input, trust="user_supplied", source="HarmBench text behavior"),
                ],
                step_candidate={
                    "available": False,
                    "tool_name": None,
                    "tool_args": {},
                    "thought": "",
                    "source": "HarmBench direct model behavior",
                },
                provenance={
                    "source_type": "user_prompt",
                    "source_trust": "user_supplied",
                    "sink_type": "model_response",
                    "target_sink": None,
                    "value_flow": "none",
                },
                target={
                    "type": "harmful_policy_behavior",
                    "behavior_id": behavior_id,
                    "semantic_category": item.get("SemanticCategory"),
                    "functional_category": item.get("FunctionalCategory"),
                    "optimizer_target": targets_text.get(behavior_id),
                },
                judge={"type": "official", "name": "HarmBench text classifier"},
                compatible_defenses=["PromptGuard2_LlamaFirewall", "DataFilter", "FIDES_deferred", "TS-Guard"],
                attack_baselines=["HarmBench_official_attacks", "PAIR", "TAP", "GCG", "AutoDAN"],
                raw_ref={"index": idx, "behavior_id": behavior_id, "tags": item.get("Tags")},
                notes="HarmBench official text behavior from harmbench_behaviors_text_all.csv.",
            )
        )

    mm_path = behavior_dir / "harmbench_behaviors_multimodal_all.csv"
    for idx, item in enumerate(load_csv(mm_path)):
        behavior = item.get("Behavior") or ""
        behavior_id = item.get("BehaviorID") or f"multimodal_{idx}"
        image_name = item.get("ImageFileName")
        image_description = item.get("RedactedImageDescription") or item.get("ImageDescription") or ""
        text_fields = [
            text_field("user_prompt.attack", behavior, trust="user_supplied", source="HarmBench multimodal behavior"),
        ]
        if image_description:
            text_fields.append(
                text_field(
                    "image_description",
                    image_description,
                    trust="benchmark_supplied",
                    source="HarmBench multimodal behavior metadata",
                )
            )
        rows.append(
            base_row(
                benchmark="HarmBench",
                suite="multimodal_all",
                source_path=str(mm_path.relative_to(ROOT)),
                split="all",
                surface="DPI",
                risk_categories=["policy"],
                taxonomy_rationale="HarmBench multimodal behavior rows are direct trusted-user harmful requests, so policy=yes.",
                controlled_fields=["user_prompt", "image"],
                clean_input="",
                attacked_input=behavior,
                text_fields=text_fields,
                step_candidate={
                    "available": False,
                    "tool_name": None,
                    "tool_args": {},
                    "thought": "",
                    "source": "HarmBench multimodal direct model behavior",
                },
                provenance={
                    "source_type": "user_prompt_and_image",
                    "source_trust": "user_supplied",
                    "sink_type": "model_response",
                    "target_sink": None,
                    "value_flow": "none",
                },
                target={
                    "type": "harmful_policy_behavior_multimodal",
                    "behavior_id": behavior_id,
                    "semantic_category": item.get("SemanticCategory"),
                    "functional_category": item.get("FunctionalCategory"),
                    "optimizer_target": targets_mm.get(behavior_id),
                    "image_file": image_name,
                },
                judge={"type": "official", "name": "HarmBench multimodal classifier"},
                compatible_defenses=["PromptGuard2_LlamaFirewall", "DataFilter", "FIDES_deferred", "TS-Guard"],
                attack_baselines=["HarmBench_official_attacks", "PAIR", "TAP", "GCG", "AutoDAN"],
                raw_ref={
                    "index": idx,
                    "behavior_id": behavior_id,
                    "tags": item.get("Tags"),
                    "image_file": image_name,
                    "source": item.get("Source"),
                },
                notes="HarmBench official multimodal behavior from harmbench_behaviors_multimodal_all.csv.",
            )
        )
    return rows


def validate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    required = [
        "schema_version",
        "case_id",
        "benchmark",
        "suite",
        "source_path",
        "split",
        "status",
        "surface",
        "risk_categories",
        "taxonomy_labels",
        "controlled_fields",
        "text_fields",
        "step_candidate",
        "provenance",
        "target",
        "judge",
        "compatible_defenses",
        "attack_baselines",
    ]
    errors: list[str] = []
    ids = set()
    for idx, row in enumerate(rows):
        for key in required:
            if key not in row:
                errors.append(f"row {idx} missing {key}")
        if row.get("case_id") in ids:
            errors.append(f"duplicate case_id {row.get('case_id')}")
        ids.add(row.get("case_id"))
        if row.get("status") != "placeholder" and not row.get("text_fields"):
            errors.append(f"row {idx} non-placeholder has no text_fields")
        for field in row.get("text_fields", []):
            if "text" not in field or "trust" not in field:
                errors.append(f"row {idx} malformed text_field")
        labels = row.get("taxonomy_labels", {})
        for label_key in ["clean", "value", "authority", "policy"]:
            if labels.get(label_key) not in {"yes", "no"}:
                errors.append(f"row {idx} malformed taxonomy label {label_key}")
        if labels.get("primary") != row.get("primary_attack_category"):
            errors.append(f"row {idx} taxonomy primary mismatch")
    by_benchmark = Counter(row["benchmark"] for row in rows)
    by_surface = Counter(row["surface"] for row in rows)
    by_risk = Counter(risk for row in rows for risk in row["risk_categories"])
    by_benchmark_primary: dict[str, Counter[str]] = defaultdict(Counter)
    by_benchmark_tags: dict[str, Counter[str]] = defaultdict(Counter)
    by_benchmark_label_yes: dict[str, Counter[str]] = defaultdict(Counter)
    by_benchmark_review_status: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        benchmark = row["benchmark"]
        by_benchmark_primary[benchmark][row.get("primary_attack_category", "unknown")] += 1
        for risk in row["risk_categories"]:
            by_benchmark_tags[benchmark][risk] += 1
        labels = row.get("taxonomy_labels", {})
        for label in ["clean", "value", "authority", "policy"]:
            if labels.get(label) == "yes":
                by_benchmark_label_yes[benchmark][label] += 1
        by_benchmark_review_status[benchmark][labels.get("review_status", "missing")] += 1
    defense_coverage = Counter(defense for row in rows for defense in row["compatible_defenses"])
    attack_coverage = Counter(attack for row in rows for attack in row["attack_baselines"])
    expected = {"ASB", "AgentDojo", "ToolSafe", "AdaptiveAttackAgent", "HarmBench"}
    missing = sorted(expected - set(by_benchmark))
    if missing:
        errors.append(f"missing benchmarks: {missing}")
    source_count_audit = build_source_count_audit(rows)
    for benchmark, audit in source_count_audit.items():
        if audit["expected_total"] != audit["manifest_total"]:
            errors.append(
                f"{benchmark} source count mismatch: expected {audit['expected_total']} manifest {audit['manifest_total']}"
            )
    return {
        "valid": not errors,
        "errors": errors,
        "n_rows": len(rows),
        "by_benchmark": dict(sorted(by_benchmark.items())),
        "by_surface": dict(sorted(by_surface.items())),
        "by_risk": dict(sorted(by_risk.items())),
        "by_benchmark_primary_attack_category": {
            benchmark: dict(sorted(counter.items()))
            for benchmark, counter in sorted(by_benchmark_primary.items())
        },
        "by_benchmark_risk_tags": {
            benchmark: dict(sorted(counter.items()))
            for benchmark, counter in sorted(by_benchmark_tags.items())
        },
        "by_benchmark_label_yes": {
            benchmark: dict(sorted(counter.items()))
            for benchmark, counter in sorted(by_benchmark_label_yes.items())
        },
        "by_benchmark_review_status": {
            benchmark: dict(sorted(counter.items()))
            for benchmark, counter in sorted(by_benchmark_review_status.items())
        },
        "defense_coverage": dict(sorted(defense_coverage.items())),
        "attack_coverage": dict(sorted(attack_coverage.items())),
        "source_count_audit": source_count_audit,
    }


def len_json_behaviors(path: Path) -> int:
    data = load_json(path)
    if isinstance(data, dict) and "behaviors" in data:
        return len(data["behaviors"])
    return len(data)


def build_source_count_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_benchmark = Counter(row["benchmark"] for row in rows)
    audit: dict[str, Any] = {}

    asb_tasks = load_jsonl(ROOT / "benchmarks" / "ASB" / "data" / "agent_task.jsonl")
    asb_tools = load_jsonl(ROOT / "benchmarks" / "ASB" / "data" / "all_attack_tools.jsonl")
    asb_tasks_by_agent = {row["agent_name"]: len(row.get("tasks") or []) for row in asb_tasks}
    asb_rows_by_matching_agent = sum(asb_tasks_by_agent.get(tool.get("Corresponding Agent"), 0) for tool in asb_tools)
    asb_surfaces = 3
    audit["ASB"] = {
        "components": {
            "matched task-tool pairs": asb_rows_by_matching_agent,
            "surfaces per task-tool": asb_surfaces,
        },
        "expected_total": asb_rows_by_matching_agent * asb_surfaces,
        "manifest_total": by_benchmark.get("ASB", 0),
    }

    adaptive_dir = ROOT / "benchmarks" / "AdaptiveAttackAgent" / "InjecAgent" / "data"
    adaptive_components = {
        "direct_harm base": len_json_behaviors(adaptive_dir / "test_cases_dh_base.json"),
        "direct_harm enhanced": len_json_behaviors(adaptive_dir / "test_cases_dh_enhanced.json"),
        "data_stealing base": len_json_behaviors(adaptive_dir / "test_cases_ds_base.json"),
        "data_stealing enhanced": len_json_behaviors(adaptive_dir / "test_cases_ds_enhanced.json"),
    }
    audit["AdaptiveAttackAgent"] = {
        "components": adaptive_components,
        "expected_total": sum(adaptive_components.values()),
        "manifest_total": by_benchmark.get("AdaptiveAttackAgent", 0),
    }

    agentdojo_dir = ROOT / "benchmarks" / "ToolSafe" / "TS-Bench" / "agentdojo-traj"
    agentdojo_traj = {
        f"TS-Bench {path.stem}": len_json_behaviors(path)
        for path in sorted(agentdojo_dir.glob("*.json"))
    }
    static_templates = sum(
        1
        for row in rows
        if row["benchmark"] == "AgentDojo" and not str(row["suite"]).startswith("TS-Bench/")
    )
    agentdojo_components = {**agentdojo_traj, "static injection templates": static_templates}
    audit["AgentDojo"] = {
        "components": agentdojo_components,
        "expected_total": sum(agentdojo_components.values()),
        "manifest_total": by_benchmark.get("AgentDojo", 0),
    }

    toolsafe_components = {
        "AgentSafetyBench released": len_json_behaviors(
            ROOT / "benchmarks" / "ToolSafe" / "benchmark" / "agent_safetybench" / "data" / "released_data.json"
        ),
        "TS-Bench AgentHarm harmful steps": len_json_behaviors(
            ROOT / "benchmarks" / "ToolSafe" / "TS-Bench" / "agentharm-traj" / "harmful_steps.json"
        ),
        "TS-Bench AgentHarm benign steps": len_json_behaviors(
            ROOT / "benchmarks" / "ToolSafe" / "TS-Bench" / "agentharm-traj" / "benign_steps.json"
        ),
        "AgentHarm public harmful": len_json_behaviors(
            ROOT / "benchmarks" / "ToolSafe" / "benchmark" / "agentharm" / "dataset" / "harmful_behaviors_test_public.json"
        ),
        "AgentHarm public benign": len_json_behaviors(
            ROOT / "benchmarks" / "ToolSafe" / "benchmark" / "agentharm" / "dataset" / "benign_behaviors_test_public.json"
        ),
    }
    audit["ToolSafe"] = {
        "components": toolsafe_components,
        "expected_total": sum(toolsafe_components.values()),
        "manifest_total": by_benchmark.get("ToolSafe", 0),
    }

    harmbench_dir = ROOT / "benchmarks" / "HarmBench" / "data" / "behavior_datasets"
    harmbench_components = {
        "text all": len(load_csv(harmbench_dir / "harmbench_behaviors_text_all.csv")),
        "multimodal all": len(load_csv(harmbench_dir / "harmbench_behaviors_multimodal_all.csv")),
    }
    audit["HarmBench"] = {
        "components": harmbench_components,
        "expected_total": sum(harmbench_components.values()),
        "manifest_total": by_benchmark.get("HarmBench", 0),
    }

    return dict(sorted(audit.items()))


def render_attack_category_table(summary: dict[str, Any]) -> str:
    benchmarks = sorted(summary["by_benchmark"].keys())
    categories = ["authority", "value", "policy"]
    source_audit = summary.get("source_count_audit", {})
    lines = [
        "# Benchmark Attack Category Coverage",
        "",
        "Generated by `python code/build_benchmark_manifest.py`.",
        "",
        "Each manifest row has exactly one `primary_attack_category`, so `Authority + Value + Policy + Clean / Other` must equal `Manifest Total`.",
        "",
        "| Benchmark | Source Components Checked | Expected Total | Manifest Total | Authority | Value | Policy | Clean / Other | Split Sum | Full Count OK |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    primary = summary["by_benchmark_primary_attack_category"]
    for benchmark in benchmarks:
        row = primary.get(benchmark, {})
        total = summary["by_benchmark"].get(benchmark, 0)
        authority = row.get("authority", 0)
        value = row.get("value", 0)
        policy = row.get("policy", 0)
        other = total - sum(row.get(cat, 0) for cat in categories)
        split_sum = authority + value + policy + other
        audit = source_audit.get(benchmark, {})
        expected = audit.get("expected_total", total)
        components = audit.get("components", {})
        component_text = "<br>".join(f"{name}={count}" for name, count in components.items()) or "N/A"
        ok = "yes" if expected == total == split_sum else "no"
        lines.append(
            f"| {benchmark} | {component_text} | {expected} | {total} | {authority} | {value} | {policy} | {other} | {split_sum} | {ok} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    rows.extend(build_asb_rows())
    rows.extend(build_adaptive_attack_agent_rows())
    rows.extend(build_agentdojo_rows())
    rows.extend(build_agentdojo_tsbench_rows())
    rows.extend(build_toolsafe_rows())
    rows.extend(build_harmbench_rows())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary = validate(rows)
    summary["manifest_path"] = str(args.out.relative_to(ROOT))
    summary_path = args.out.with_name("benchmark_manifest_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    table_path = args.out.with_name("benchmark_attack_category_table.md")
    table_path.write_text(render_attack_category_table(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not summary["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
