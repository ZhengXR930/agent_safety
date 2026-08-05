"""Build the trusted MSB case manifest from official dataset metadata."""

import json
from pathlib import Path

import yaml

from code.manifest.mcptox import registration


DEFAULT_CASE_PATH = Path(__file__).resolve().parent / "data" / "msb_cases.json"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()
            if line.strip()]


def _slug(task: str) -> str:
    return task[:20].replace(" ", "_").replace(":", "").replace(
        "/", "").replace(".", "")


def _attack_tool_exists(root: Path, agent: str, tool: str) -> bool:
    if agent == "image_generation":
        return False
    directory = root / "data/tools/attack_tools" / agent
    return directory.is_dir() and tool in {
        path.name for path in directory.iterdir()}


def build(root: Path, config_path: Path) -> dict:
    config = yaml.safe_load(config_path.read_text())
    requested_types = config["attack_type"]
    available = _jsonl(root / "data/attack_type.jsonl")[-1]["attack_type"]
    attack_types = available if requested_types == ["all"] else requested_types
    tasks = _jsonl(root / "data/attack_task.jsonl")
    if config.get("attack_task", ["all"]) != ["all"]:
        tasks = [row for row in tasks
                 if row["attack_task"] in config["attack_task"]]
    agents = _jsonl(root / "data/agent_task.jsonl")
    if config.get("agents", ["all"]) != ["all"]:
        agents = [row for row in agents if row["agent_name"] in config["agents"]]
    skipped = set(config.get("skip_tools", []))
    restricted = ("tool_transfer", "name_overlap", "out_of_scope_parameter",
                  "preference_manipulation")
    source_only = {"out_of_scope_parameter", "search_term_deception",
                   "tool_transfer"}
    cases = []
    for attack_type in attack_types:
        for agent_row in agents:
            agent = agent_row["agent_name"]
            if ((agent == "information_retrieval") !=
                    (attack_type == "search_term_deception")):
                continue
            for task_tool in agent_row["task_tool"]:
                task, tool = task_tool["task"], task_tool["tool"]
                if (any(name in attack_type for name in restricted) and
                        not _attack_tool_exists(root, agent, tool)):
                    continue
                if tool in skipped and attack_type not in source_only:
                    continue
                for attack in tasks:
                    case_id = "#".join((attack_type, agent, _slug(task), tool,
                                        attack["attack_task"]))
                    cases.append({
                        "case_id": case_id, "attack_type": attack_type,
                        "agent": agent, "system_prompt": agent_row["system_prompt"],
                        "task": task, "tool": tool,
                        "attack_task": attack["attack_task"],
                        "implementation": attack["implementation"],
                    })
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise RuntimeError("MSB case IDs collide after official task truncation")
    return {"schema": "msb-case-manifest-v1",
            "source_config": str(config_path.resolve()),
            "skip_tools": sorted(skipped), "case_count": len(cases),
            "cases": cases}


def runtime_manifest(tool_name: str, description: str):
    """Return the trusted Tool boundaries for one MSB MCP episode."""
    tools = [
        {"name": str(tool_name), "description": str(description),
         "argument_types": {"query": "natural_language"},
         "inputSchema": {"type": "object", "properties": {
             "query": {"type": "string", "x-task-derived": True}},
             "required": ["query"], "additionalProperties": False}},
        {"name": "write_file", "description": "Write content to a file path.",
         "argument_types": {"path": "path", "content": "natural_language"},
         "inputSchema": {"type": "object", "properties": {
             "path": {"type": "string"}, "content": {"type": "string"}},
             "required": ["path", "content"], "additionalProperties": False}},
        {"name": "read_text_file", "description": "Read a local text file.",
         "argument_types": {"path": "path"},
         "inputSchema": {"type": "object", "properties": {
             "path": {"type": "string"}}, "required": ["path"],
             "additionalProperties": False}},
    ]
    registrations = [
        # The official MSB task Tool is an information-retrieval boundary.
        # It emits a data Receipt but has no persistent outbound effect.  The
        # support writer remains an Effect and is therefore still WRAP-gated.
        registration(tool_name, tools[0], effect=False),
        registration("support-filesystem", tools[1], observation=False),
        registration("support-filesystem", tools[2], effect=False),
    ]
    mapping = {tools[index]["name"]: registrations[index]["name"]
               for index in range(len(tools))}
    return tools, registrations, mapping
